import asyncio
from functools import wraps

from quart import current_app

from anonstream.chat import broadcast
from anonstream.wrappers import with_timestamp
from anonstream.helpers.user import is_visible

CONFIG = current_app.config
MESSAGES = current_app.messages
USERS_BY_TOKEN = current_app.users_by_token
USERS = current_app.users

def with_period(period):
    def periodically(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            await asyncio.sleep(period)
            while True:
                if current_app.shutting_down:
                    break
                else:
                    f(*args, **kwargs)
                    await asyncio.sleep(period)

        return wrapper

    return periodically

@with_period(CONFIG['CHECKUP_PERIOD_USER'])
@with_timestamp
def t_sunset_users(timestamp):
    tokens = []
    for token in USERS_BY_TOKEN:
        user = USERS_BY_TOKEN[token]
        if not is_visible(timestamp, MESSAGES, user):
            tokens.append(token)

    token_hashes = []
    while tokens:
        token = tokens.pop()
        token_hash = USERS_BY_TOKEN.pop(token)['token_hash']
        token_hashes.append(token_hash)

    if token_hashes:
        broadcast(
            users=USERS,
            payload={
                'type': 'rem-users',
                'token_hashes': token_hashes,
            },
        )

current_app.add_background_task(t_sunset_users)
