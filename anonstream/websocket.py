import asyncio

from quart import current_app, websocket

from anonstream.stream import get_stream_title, get_stream_uptime
from anonstream.captcha import get_random_captcha_digest_for
from anonstream.chat import get_all_messages_for_websocket, add_chat_message, Rejected
from anonstream.user import get_all_users_for_websocket, see, verify, deverify, BadCaptcha
from anonstream.utils.chat import generate_nonce
from anonstream.utils.websocket import parse_websocket_data, Malformed

CONFIG = current_app.config

async def websocket_outbound(queue, user):
    payload = {
        'type': 'init',
        'nonce': generate_nonce(),
        'title': get_stream_title(),
        'uptime': get_stream_uptime(),
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
        receipt = await websocket.receive_json()
        see(user)
        try:
            nonce, comment, digest, answer = parse_websocket_data(receipt)
        except Malformed as e:
            error , *_ = e.args
            payload = {
                'type': 'error',
                'because': error,
            }
        else:
            try:
                verify(user, digest, answer)
            except BadCaptcha as e:
                notice, *_ = e.args
                payload = {
                    'type': 'captcha',
                    'notice': notice,
                    'digest': get_random_captcha_digest_for(user),
                }
            else:
                try:
                    markup = add_chat_message(user, nonce, comment)
                except Rejected as e:
                    notice, *_ = e.args
                    payload = {
                        'type': 'reject',
                        'notice': notice,
                    }
                else:
                    deverify(user)
                    payload = {
                        'type': 'ack',
                        'nonce': nonce,
                        'next': generate_nonce(),
                        'digest': get_random_captcha_digest_for(user),
                    }
        queue.put_nowait(payload)
