import asyncio
import itertools
from functools import wraps

from quart import current_app

from anonstream.broadcast import broadcast, broadcast_users_update
from anonstream.stream import is_online, get_stream_title, get_stream_uptime, get_stream_viewership_or_none
from anonstream.user import get_sunsettable_users
from anonstream.wrappers import with_timestamp

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
            for iteration in itertools.count():
                await f(iteration, *args, **kwargs)
                try:
                    await sleep_and_collect_task(period)
                except asyncio.CancelledError:
                    break

        return wrapper

    return periodically

@with_period(CONFIG['TASK_PERIOD_ROTATE_USERS'])
@with_timestamp
async def t_sunset_users(timestamp, iteration):
    if iteration == 0:
        return

    # Broadcast a users update, in case any users being
    # removed have been mutated or are new.
    broadcast_users_update()

    token_hashes = []
    users = list(get_sunsettable_users(timestamp))
    while users:
        user = users.pop()
        USERS_BY_TOKEN.pop(user['token'])
        token_hashes.append(user['token_hash'])

    if token_hashes:
        broadcast(
            users=USERS,
            payload={
                'type': 'rem-users',
                'token_hashes': token_hashes,
            },
        )

@with_period(CONFIG['TASK_PERIOD_ROTATE_CAPTCHAS'])
async def t_expire_captchas(iteration):
    if iteration == 0:
        return

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
async def t_broadcast_users_update(iteration):
    if iteration == 0:
        return
    else:
        broadcast_users_update()

@with_period(CONFIG['TASK_PERIOD_BROADCAST_STREAM_INFO_UPDATE'])
async def t_broadcast_stream_info_update(iteration):
    if iteration == 0:
        title = await get_stream_title()
        uptime = get_stream_uptime()
        viewership = get_stream_viewership_or_none(uptime)
        current_app.stream_title = title
        current_app.stream_uptime = uptime
        current_app.stream_viewership = viewership
    else:
        payload = {}

        # Check if the stream title has changed
        title = await get_stream_title()
        if current_app.stream_title != title:
            current_app.stream_title = title
            payload['title'] = title

        # Check if the stream uptime has changed more or less than expected
        if current_app.stream_uptime is None:
            expected_uptime = None
        else:
            expected_uptime = (
                current_app.stream_uptime
                + CONFIG['TASK_PERIOD_BROADCAST_STREAM_INFO_UPDATE']
            )
        uptime = get_stream_uptime()
        current_app.stream_uptime = uptime
        if uptime is None and expected_uptime is None:
            pass
        elif uptime is None or expected_uptime is None:
            payload['uptime'] = uptime
        elif abs(uptime - expected_uptime) >= 0.0625:
            payload['uptime'] = uptime

        # Check if viewership has changed
        viewership = get_stream_viewership_or_none(uptime)
        if current_app.stream_viewership != viewership:
            current_app.stream_viewership = viewership
            payload['viewership'] = viewership

        if payload:
            broadcast(USERS, payload={'type': 'info', **payload})

current_app.add_background_task(t_sunset_users)
current_app.add_background_task(t_expire_captchas)
current_app.add_background_task(t_broadcast_users_update)
current_app.add_background_task(t_broadcast_stream_info_update)
