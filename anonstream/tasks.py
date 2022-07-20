# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import itertools
from functools import wraps

from quart import current_app, websocket

from anonstream.broadcast import broadcast, broadcast_users_update
from anonstream.stream import is_online, get_stream_title, get_stream_uptime_and_viewership
from anonstream.user import get_absent_users, get_sunsettable_users, deverify, ensure_allowedness, AllowednessException
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

@with_period(CONFIG['TASK_ROTATE_EYES'])
@with_timestamp()
async def t_delete_eyes(timestamp, iteration):
    if iteration == 0:
        return
    else:
        for user in USERS:
            to_delete = []
            for eyes_id, eyes in user['eyes']['current'].items():
                renewed_ago = timestamp - eyes['renewed']
                if renewed_ago >= CONFIG['FLOOD_VIDEO_EYES_EXPIRE_AFTER']:
                    to_delete.append(eyes_id)
            for eyes_id in to_delete:
                user['eyes']['current'].pop(eyes_id)

@with_period(CONFIG['TASK_ROTATE_USERS'])
@with_timestamp()
async def t_sunset_users(timestamp, iteration):
    if iteration == 0:
        return

    # De-access absent users
    absent_users = tuple(get_absent_users(timestamp))
    for user in absent_users:
        user['verified'] = None
    # Absent users should have no connected websockets,
    # so in normal operation this should always be a no-op
    broadcast(users=absent_users, payload={'type': 'kick'})

    # Remove as many absent users as possible

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

@with_period(CONFIG['TASK_ROTATE_CAPTCHAS'])
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

@with_period(CONFIG['TASK_ROTATE_WEBSOCKETS'])
@with_timestamp()
async def t_close_websockets(timestamp, iteration):
    THRESHOLD = CONFIG['TASK_BROADCAST_PING'] * 1.5 + 4.0
    if iteration == 0:
        return
    else:
        for user in USERS:
            for queue in user['websockets']:
                # Check allowedness
                try:
                    ensure_allowedness(user, timestamp=timestamp)
                except AllowednessException:
                    queue.put_nowait({'type': 'kick'})
                # Check expiry
                last_pong = user['websockets'][queue]
                last_pong_ago = timestamp - last_pong
                if last_pong_ago > THRESHOLD:
                    queue.put_nowait({'type': 'close'})

@with_period(CONFIG['TASK_BROADCAST_PING'])
async def t_broadcast_ping(iteration):
    if iteration == 0:
        return
    else:
        broadcast(USERS, payload={'type': 'ping'})

@with_period(CONFIG['TASK_BROADCAST_USERS_UPDATE'])
async def t_broadcast_users_update(iteration):
    if iteration == 0:
        return
    else:
        broadcast_users_update()

@with_period(CONFIG['TASK_BROADCAST_STREAM_INFO_UPDATE'])
@with_timestamp(precise=True)
async def t_broadcast_stream_info_update(timestamp, iteration):
    if iteration == 0:
        title = await get_stream_title()
        uptime, viewership = get_stream_uptime_and_viewership(rounded=False)
        current_app.stream_title = title
        current_app.stream_uptime = uptime
        current_app.stream_viewership = viewership
    else:
        info = {}
        title = await get_stream_title()
        uptime, viewership = get_stream_uptime_and_viewership(rounded=False)

        # Check if the stream title has changed
        if current_app.stream_title != title:
            current_app.stream_title = title
            info['title'] = title

        # Check if the stream uptime has changed unexpectedly
        last_uptime, current_app.stream_uptime = (
            current_app.stream_uptime, uptime
        )
        if last_uptime is None:
            projected_uptime = None
        else:
            last_info_task_ago = timestamp - current_app.last_info_task
            projected_uptime = last_uptime + last_info_task_ago
        if uptime is None and projected_uptime is None:
            stats_changed = False
        elif uptime is None or projected_uptime is None:
            stats_changed = True
        else:
            stats_changed = abs(uptime - projected_uptime) >= 0.5

        # Check if viewership has changed
        if current_app.stream_viewership != viewership:
            current_app.stream_viewership = viewership
            stats_changed = True

        # Broadcast iff anything has changed
        if stats_changed:
            if uptime is None:
                info['stats'] = None
            else:
                info['stats'] = {
                    'uptime': round(uptime, 2),
                    'viewership': viewership,
                }
        if info:
            broadcast(USERS, payload={'type': 'info', **info})

    current_app.last_info_task = timestamp

current_app.add_background_task(t_delete_eyes)
current_app.add_background_task(t_sunset_users)
current_app.add_background_task(t_expire_captchas)
current_app.add_background_task(t_close_websockets)
current_app.add_background_task(t_broadcast_ping)
current_app.add_background_task(t_broadcast_users_update)
current_app.add_background_task(t_broadcast_stream_info_update)
