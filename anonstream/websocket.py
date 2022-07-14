# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json

from quart import current_app, websocket

from anonstream.stream import get_stream_title, get_stream_uptime_and_viewership
from anonstream.captcha import get_random_captcha_digest_for
from anonstream.chat import get_all_messages_for_websocket, add_chat_message, Rejected
from anonstream.user import get_all_users_for_websocket, see, reading, verify, deverify, BadCaptcha, try_change_appearance, ensure_allowedness, AllowednessException
from anonstream.wrappers import with_timestamp, get_timestamp
from anonstream.helpers.chat import get_emotes_for_websocket
from anonstream.utils.chat import generate_nonce
from anonstream.utils.user import identifying_string
from anonstream.utils.websocket import parse_websocket_data, Malformed, WS

CONFIG = current_app.config

async def websocket_outbound(queue, user):
    # This function does NOT check alllowedness at first, only later.
    # Allowedness is assumed to be checked beforehand (by the route handler).
    # These first two websocket messages are always sent.
    await websocket.send_json({'type': 'ping'})
    await websocket.send_json({
        'type': 'init',
        'nonce': generate_nonce(),
        'title': await get_stream_title(),
        'stats': get_stream_uptime_and_viewership(for_websocket=True),
        'messages': get_all_messages_for_websocket(),
        'users': get_all_users_for_websocket(),
        'default': {
            True: CONFIG['DEFAULT_HOST_NAME'],
            False: CONFIG['DEFAULT_ANON_NAME'],
        },
        'scrollback': CONFIG['MAX_CHAT_SCROLLBACK'],
        'digest': get_random_captcha_digest_for(user),
        'pingpong': CONFIG['TASK_BROADCAST_PING'],
        'emotes': get_emotes_for_websocket(),
    })
    while True:
        payload = await queue.get()
        if payload['type'] == 'kick':
            await websocket.send_json(payload)
            await websocket.close(1001)
            break
        elif payload['type'] == 'close':
            await websocket.close(1011)
            break
        else:
            try:
                ensure_allowedness(user)
            except AllowednessException:
                websocket.send_json({'type': 'kick'})
                await websocket.close(1001)
                break
            else:
                await websocket.send_json(payload)

async def websocket_inbound(queue, user):
    while True:
        # Read from websocket
        try:
            receipt = await websocket.receive_json()
        except json.JSONDecodeError:
            receipt = None
        finally:
            timestamp = get_timestamp()
            see(user, timestamp=timestamp)

        # Prepare response
        try:
            ensure_allowedness(user)
        except AllowednessException:
            payload = {'type': 'kick'}
        else:
            try:
                receipt_type, parsed = parse_websocket_data(receipt)
            except Malformed as e:
                error , *_ = e.args
                payload = {
                    'type': 'error',
                    'because': error,
                }
            else:
                match receipt_type:
                    case WS.MESSAGE:
                        handle = handle_inbound_message
                    case WS.APPEARANCE:
                        handle = handle_inbound_appearance
                    case WS.CAPTCHA:
                        handle = handle_inbound_captcha
                    case WS.PONG:
                        handle = handle_inbound_pong
                payload = handle(timestamp, queue, user, *parsed)

        # Write to websocket
        if payload is not None:
            queue.put_nowait(payload)

def handle_inbound_pong(timestamp, queue, user):
    print(f'[pong] {identifying_string(user)}')
    user['last']['reading'] = timestamp
    user['websockets'][queue] = timestamp
    return None

def handle_inbound_captcha(timestamp, queue, user):
    return {
        'type': 'captcha',
        'digest': get_random_captcha_digest_for(user),
    }

def handle_inbound_appearance(timestamp, queue, user, name, color, password, want_tripcode):
    errors = try_change_appearance(user, name, color, password, want_tripcode)
    if errors:
        return {
            'type': 'appearance',
            'errors': [error.args for error in errors],
        }
    else:
        return {
            'type': 'appearance',
            'result': 'Changed appearance',
            'name': user['name'],
            'color': user['color'],
            #'tripcode': user['tripcode'],
        }

def handle_inbound_message(timestamp, queue, user, nonce, comment, digest, answer):
    try:
        verification_happened = verify(user, digest, answer)
    except BadCaptcha as e:
        notice, *_ = e.args
        message_was_added = False
    else:
        try:
            message_was_added = add_chat_message(
                user,
                nonce,
                comment,
                ignore_empty=verification_happened,
            )
        except Rejected as e:
            notice, *_ = e.args
            message_was_added = False
        else:
            notice = None
            if message_was_added:
                deverify(user, timestamp=timestamp)
    return {
        'type': 'ack',
        'nonce': nonce,
        'next': generate_nonce(),
        'notice': notice,
        'clear': message_was_added,
        'digest': get_random_captcha_digest_for(user),
    }
