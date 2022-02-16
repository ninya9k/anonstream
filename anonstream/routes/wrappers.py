import time
from functools import wraps

from quart import current_app, request, abort, make_response
from werkzeug.security import check_password_hash

from anonstream.users import sunset, user_for_websocket
from anonstream.websocket import broadcast
from anonstream.utils.users import generate_token, generate_user

def check_auth(context):
    auth = context.authorization
    return (
        auth is not None
        and auth.type == "basic"
        and auth.username == current_app.config["AUTH_USERNAME"]
        and check_password_hash(current_app.config["AUTH_PWHASH"], auth.password)
    )

def auth_required(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        if check_auth(request):
            return await f(*args, **kwargs)
        hint = 'The broadcaster should log in with the credentials printed ' \
               'in their terminal.'
        body = (
            f'<p>{hint}</p>'
            if request.authorization is None else
             '<p>Wrong username or password. Refresh the page to try again.</p>'
            f'<p>{hint}</p>'
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
                token = current_app.config['AUTH_TOKEN']
            else:
                token = context.args.get('token') or context.cookies.get('token') or generate_token()

            # Remove non-visible absent users
            token_hashes = sunset(
                messages=current_app.chat['messages'].values(),
                users=current_app.users,
            )
            if len(token_hashes) > 0:
                await broadcast(
                    current_app.websockets,
                    payload={
                        'type': 'rem-users',
                        'token_hashes': token_hashes,
                    }
                )

            # Update / create user
            user = current_app.users.get(token)
            if user is not None:
                user['seen']['last'] = timestamp
            else:
                user = generate_user(
                    secret=current_app.config['SECRET_KEY'],
                    token=token,
                    broadcaster=broadcaster,
                    timestamp=timestamp,
                )
                current_app.users[token] = user
                await broadcast(
                    current_app.websockets,
                    payload={
                        'type': 'add-user',
                        'user': user_for_websocket(user),
                    }
                )

            # Set cookie
            response = await f(user, *args, **kwargs)
            if context.cookies.get('token') != token:
                response = await make_response(response)
                response.headers['Set-Cookie'] = f'token={token}; path=/'
            return response

        return wrapper

    return with_user_from_context
