import asyncio
import json

from quart import current_app, websocket

from anonstream.stream import get_stream_title, get_stream_uptime, get_stream_viewership_or_none
from anonstream.captcha import get_random_captcha_digest_for
from anonstream.chat import get_all_messages_for_websocket, add_chat_message, Rejected
from anonstream.user import get_all_users_for_websocket, see, verify, deverify, BadCaptcha
from anonstream.utils.chat import generate_nonce
from anonstream.utils.websocket import parse_websocket_data, Malformed

CONFIG = current_app.config

async def websocket_outbound(queue, user):
    uptime = get_stream_uptime()
    viewership = get_stream_viewership_or_none(uptime)
    payload = {
        'type': 'init',
        'nonce': generate_nonce(),
        'title': await get_stream_title(),
        'uptime': uptime,
        'viewership': viewership,
        'messages': get_all_messages_for_websocket(),
        'users': get_all_users_for_websocket(),
        'default': {
            True: CONFIG['DEFAULT_HOST_NAME'],
            False: CONFIG['DEFAULT_ANON_NAME'],
        },
        'scrollback': CONFIG['MAX_CHAT_SCROLLBACK'],
        'digest': get_random_captcha_digest_for(user),
    }
    await websocket.send_json(payload)
    while True:
        payload = await queue.get()
        await websocket.send_json(payload)

async def websocket_inbound(queue, user):
    while True:
        try:
            receipt = await websocket.receive_json()
        except json.JSONDecodeError:
            receipt = None
        finally:
            see(user)
        try:
            parsed = parse_websocket_data(receipt)
        except Malformed as e:
            error , *_ = e.args
            payload = {
                'type': 'error',
                'because': error,
            }
        else:
            match parsed:
                case [nonce, comment, digest, answer]:
                    payload = handle_inbound_message(user, *parsed)

                case None:
                    payload = handle_inbound_captcha(user)

        queue.put_nowait(payload)

def handle_inbound_captcha(user):
    return {
        'type': 'captcha',
        'digest': get_random_captcha_digest_for(user),
    }

def handle_inbound_message(user, nonce, comment, digest, answer):
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
                deverify(user)
    return {
        'type': 'ack',
        'nonce': nonce,
        'next': generate_nonce(),
        'notice': notice,
        'clear': message_was_added,
        'digest': get_random_captcha_digest_for(user),
    }
