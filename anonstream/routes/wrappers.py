# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import re
import string
import time
from functools import wraps

from quart import current_app, request, abort, make_response, render_template, request
from werkzeug.security import check_password_hash

from anonstream.broadcast import broadcast
from anonstream.user import see
from anonstream.helpers.user import generate_user
from anonstream.utils.user import generate_token, Presence

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

def check_auth(context):
    auth = context.authorization
    return (
        auth is not None
        and auth.type == "basic"
        and auth.username == CONFIG["AUTH_USERNAME"]
        and check_password_hash(CONFIG["AUTH_PWHASH"], auth.password)
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
            body = (
                f'<!doctype html>\n'
                f'<p>{hint}</p>\n'
            )
        else:
            body = (
                f'<!doctype html>\n'
                f'<p>Wrong username or password. Refresh the page to try again.</p>\n'
                f'<p>{hint}</p>\n'
            )
        return body, 401, {'WWW-Authenticate': 'Basic'}

    return wrapper

def with_user_from(context):
    def with_user_from_context(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            timestamp = int(time.time())

            # Check if broadcaster
            broadcaster = check_auth(context)
            if broadcaster:
                token = CONFIG['AUTH_TOKEN']
            else:
                token = (
                    context.args.get('token')
                    or context.cookies.get('token')
                    or generate_token()
                )

            # Reject invalid tokens
            if not RE_TOKEN.fullmatch(token):
                raise abort(400)

            # Update / create user
            user = USERS_BY_TOKEN.get(token)
            if user is not None:
                see(user)
            else:
                user = generate_user(
                    timestamp=timestamp,
                    token=token,
                    broadcaster=broadcaster,
                    presence=Presence.NOTWATCHING,
                )
                USERS_BY_TOKEN[token] = user

                # Add to the users update buffer
                USERS_UPDATE_BUFFER.add(token)

            # Set cookie
            response = await f(user, *args, **kwargs)
            if context.cookies.get('token') != token:
                response = await make_response(response)
                response.headers['Set-Cookie'] = f'token={token}; path=/'
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
