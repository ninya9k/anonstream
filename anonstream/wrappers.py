from functools import wraps

from quart import current_app
from werkzeug.security import check_password_hash

from anonstream.utils.token import generate_token

def check_auth(context):
    auth = context.authorization
    return (
        auth is not None
        and auth.type == "basic"
        and auth.username == current_app.config["AUTH_USERNAME"]
        and check_password_hash(auth.password, current_app.config["AUTH_PWHASH"])
    )

def auth_required(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        if check_auth(request):
            return await func(*args, **kwargs)
        else:
            abort(401)

    return wrapper

def with_token_from(context):
    def with_token_from_context(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            if check_auth(context):
                token = current_app.config['AUTH_TOKEN']
            else:
                token = context.args.get('token') or generate_token()
            return await f(token, *args, **kwargs)

        return wrapper
    return with_token_from_context
