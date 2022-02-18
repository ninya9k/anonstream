import asyncio

from quart import current_app, websocket

from anonstream.stream import get_stream_title, get_stream_uptime
from anonstream.chat import messages_for_websocket, add_chat_message, Rejected
from anonstream.user import users_for_websocket, see
from anonstream.wrappers import with_first_argument
from anonstream.helpers.user import is_present
from anonstream.utils.chat import generate_nonce
from anonstream.utils.websocket import parse_websocket_data, Malformed

CONFIG = current_app.config

async def websocket_outbound(queue):
    payload = {
        'type': 'init',
        'nonce': generate_nonce(),
        'title': get_stream_title(),
        'uptime': get_stream_uptime(),
        'messages': messages_for_websocket(),
        'users': users_for_websocket(),
        'default': {
            True: CONFIG['DEFAULT_HOST_NAME'],
            False: CONFIG['DEFAULT_ANON_NAME'],
        },
        'scrollback': CONFIG['MAX_CHAT_SCROLLBACK'],
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
            nonce, comment = parse_websocket_data(receipt)
        except Malformed as e:
            error , *_ = e.args
            payload = {
                'type': 'error',
                'because': error,
            }
        else:
            try:
                markup = await add_chat_message(user, nonce, comment)
            except Rejected as e:
                notice, *_ = e.args
                payload = {
                    'type': 'reject',
                    'notice': notice,
                }
            else:
                payload = {
                    'type': 'ack',
                    'nonce': nonce,
                    'next': generate_nonce(),
                }
        await queue.put(payload)
