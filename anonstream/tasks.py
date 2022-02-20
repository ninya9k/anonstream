import asyncio
from functools import wraps

from quart import current_app

from anonstream.broadcast import broadcast, broadcast_users_update
from anonstream.wrappers import with_timestamp
from anonstream.helpers.user import is_visible

CONFIG = current_app.config
MESSAGES = current_app.messages
USERS_BY_TOKEN = current_app.users_by_token
USERS = current_app.users
CAPTCHAS = current_app.captchas
CAPTCHA_SIGNER = current_app.captcha_signer

async def sleep_and_collect_task(delay):
    coro = asyncio.sleep(delay)
    task = asyncio.create_task(coro)
    current_app.background_sleep.add(task)
    try:
        await task
    finally:
        current_app.background_sleep.remove(task)

def with_period(period):
    def periodically(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    await sleep_and_collect_task(period)
                except asyncio.CancelledError:
                    break
                f(*args, **kwargs)

        return wrapper

    return periodically

@with_period(CONFIG['TASK_PERIOD_ROTATE_USERS'])
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

        # Broadcast a users update, in case any users being
        # removed have been mutated or are new.
        broadcast_users_update()

    if token_hashes:
        broadcast(
            users=USERS,
            payload={
                'type': 'rem-users',
                'token_hashes': token_hashes,
            },
        )

@with_period(CONFIG['TASK_PERIOD_ROTATE_CAPTCHAS'])
def t_expire_captchas():
    to_delete = []
    for digest in CAPTCHAS:
        valid = CAPTCHA_SIGNER.validate(
            digest,
            max_age=CONFIG['CAPTCHA_LIFETIME'],
        )
        if not valid:
            to_delete.append(digest)
    for digest in to_delete:
        CAPTCHAS.pop(digest)

@with_period(CONFIG['TASK_PERIOD_BROADCAST_USERS_UPDATE'])
def t_broadcast_users_update():
    broadcast_users_update()

current_app.add_background_task(t_sunset_users)
current_app.add_background_task(t_expire_captchas)
current_app.add_background_task(t_broadcast_users_update)
