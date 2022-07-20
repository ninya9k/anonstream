# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import hmac
import re
import string
from functools import wraps
from urllib.parse import quote, unquote

from quart import current_app, request, make_response, render_template, request, url_for, Markup
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden
from werkzeug.security import check_password_hash

from anonstream.broadcast import broadcast
from anonstream.user import ensure_allowedness, Blacklisted, SecretClub
from anonstream.helpers.user import generate_user
from anonstream.utils.user import generate_token, Presence
from anonstream.wrappers import get_timestamp

CONFIG = current_app.config
MESSAGES = current_app.messages
USERS_BY_TOKEN = current_app.users_by_token
USERS = current_app.users
USERS_UPDATE_BUFFER = current_app.users_update_buffer

TOKEN_ALPHABET = (
    string.digits
    + string.ascii_lowercase
    + string.ascii_uppercase
    + string.punctuation
    + ' '
)
RE_TOKEN = re.compile(r'[%s]{1,256}' % re.escape(TOKEN_ALPHABET))

def try_unquote(string):
    if string is None:
        return None
    else:
        return unquote(string)

def check_auth(context):
    auth = context.authorization
    return (
        auth is not None
        and auth.type == 'basic'
        and auth.username == CONFIG['AUTH_USERNAME']
        and check_password_hash(CONFIG['AUTH_PWHASH'], auth.password)
    )

def auth_required(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        if check_auth(request):
            return await f(*args, **kwargs)
        hint = (
            'The broadcaster should log in with the credentials printed in '
            'their terminal.'
        )
        if request.authorization is None:
            description = hint
        else:
            description = Markup(
                f'Wrong username or password.  Refresh the page to try again.  '
                f'<br>'
                f'{hint}'
            )
        error = Unauthorized(description)
        response = await current_app.handle_http_exception(error)
        response = await make_response(response)
        response.headers['WWW-Authenticate'] = 'Basic'
        return response
    return wrapper

def generate_and_add_user(
    timestamp, token=None, broadcaster=False, verified=False, headers=None,
):
    token = token or generate_token()
    user = generate_user(
        timestamp=timestamp,
        token=token,
        broadcaster=broadcaster,
        verified=verified,
        headers=headers,
    )
    USERS_BY_TOKEN[token] = user
    USERS_UPDATE_BUFFER.add(token)
    return user

def with_user_from(context, fallback_to_token=False, ignore_allowedness=False):
    def with_user_from_context(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            timestamp = get_timestamp()

            # Get token
            broadcaster = check_auth(context)
            token_from_args = context.args.get('token')
            token_from_cookie = try_unquote(context.cookies.get('token'))
            token_from_context = token_from_args or token_from_cookie
            if broadcaster:
                token = CONFIG['AUTH_TOKEN']
            elif CONFIG['ACCESS_CAPTCHA']:
                token = token_from_context
            else:
                token = token_from_context or generate_token()

            # Reject invalid tokens
            if isinstance(token, str) and not RE_TOKEN.fullmatch(token):
                raise BadRequest(Markup(
                    f'Your token contains disallowed characters or is too '
                    f'long.  Tokens must match this regular expression: <br>'
                    f'<code>{RE_TOKEN.pattern}</code>'
                ))

            # Only logged in broadcaster may have the broadcaster's token
            if (
                not broadcaster
                and isinstance(token, str)
                and hmac.compare_digest(token, CONFIG['AUTH_TOKEN'])
            ):
                    raise Unauthorized(Markup(
                        f"You are using the broadcaster's token but you are "
                        f"not logged in.  The broadcaster should "
                        f"<a href=\"{url_for('login')}\" target=\"_top\">"
                        f"click here"
                        f"</a> "
                        f"and log in with the credentials printed in their "
                        f"terminal when they started anonstream."
                    ))

            # Create response
            user = USERS_BY_TOKEN.get(token)
            if CONFIG['ACCESS_CAPTCHA'] and not broadcaster:
                if user is not None:
                    user['last']['seen'] = timestamp
                    user['headers'] = tuple(context.headers)
                    if not ignore_allowedness:
                        assert_allowedness(timestamp, user)
                if user is not None and user['verified'] is not None:
                    response = await f(timestamp, user, *args, **kwargs)
                elif fallback_to_token:
                    #assert not broadcaster
                    response = await f(timestamp, token, *args, **kwargs)
                else:
                    raise Forbidden(Markup(
                        f"You have not solved the access captcha.  "
                        f"<a href=\"{url_for('home', token=token)}\" target=\"_top\">"
                        f"Click here."
                        f"</a>"
                    ))
            else:
                if user is not None:
                    user['last']['seen'] = timestamp
                    user['headers'] = tuple(context.headers)
                else:
                    user = generate_and_add_user(
                        timestamp,
                        token,
                        broadcaster,
                        headers=tuple(context.headers),
                    )
                if not ignore_allowedness:
                    assert_allowedness(timestamp, user)
                response = await f(timestamp, user, *args, **kwargs)

            # Set cookie
            if token_from_cookie != token:
                response = await make_response(response)
                response.headers['Set-Cookie'] = f'token={quote(token)}; path=/'

            return response

        return wrapper

    return with_user_from_context

async def render_template_with_etag(template, deferred_kwargs, **kwargs):
    render = await render_template(template, **kwargs)
    tag = hashlib.sha256(render.encode()).hexdigest()
    etag = f'W/"{tag}"'
    if request.if_none_match.contains_weak(tag):
        return '', 304, {'ETag': etag}
    else:
        rendered_template = await render_template(
            template,
            **deferred_kwargs,
            **kwargs,
        )
        return rendered_template, {'ETag': etag}

def clean_cache_headers(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        response = await f(*args, **kwargs)

        # Remove Last-Modified
        try:
            response.headers.pop('Last-Modified')
        except KeyError:
            pass

        # Obfuscate ETag
        try:
            original_etag = response.headers['ETag']
        except KeyError:
            pass
        else:
            parts = CONFIG['SECRET_KEY'] + b'etag\0' + original_etag.encode()
            tag = hashlib.sha256(parts).hexdigest()
            response.headers['ETag'] = f'"{tag}"'

        return response

    return wrapper

def etag_conditional(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        response = await f(*args, **kwargs)
        etag = response.headers.get('ETag')
        if etag is not None:
            if match := re.fullmatch(r'"(?P<tag>.+)"', etag):
                tag = match.group('tag')
                if tag in request.if_none_match:
                    return '', 304, {'ETag': etag}

        return response

    return wrapper

def assert_allowedness(timestamp, user):
    try:
        ensure_allowedness(user, timestamp=timestamp)
    except Blacklisted as e:
        raise Forbidden('You have been blacklisted.')
    except SecretClub as e:
        raise Forbidden('You have not been whitelisted.')
