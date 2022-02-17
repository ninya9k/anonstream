import asyncio

from quart import current_app, websocket

from anonstream.stream import get_stream_title, get_stream_uptime
from anonstream.chat import broadcast, add_chat_message, Rejected
from anonstream.user import users_for_websocket, see
from anonstream.wrappers import with_first_argument
from anonstream.helpers.user import is_present
from anonstream.utils.chat import generate_nonce, message_for_websocket
from anonstream.utils.websocket import parse_websocket_data, Malformed

CONFIG = current_app.config

async def websocket_outbound(queue, messages, users):
    payload = {
        'type': 'init',
        'nonce': generate_nonce(),
        'title': get_stream_title(),
        'uptime': get_stream_uptime(),
        'chat': list(map(
            with_first_argument(users)(message_for_websocket),
            messages,
        )),
        'users': users_for_websocket(messages, users),
        'default': {
            True: CONFIG['DEFAULT_HOST_NAME'],
            False: CONFIG['DEFAULT_ANON_NAME'],
        },
    }
    await websocket.send_json(payload)
    while True:
        payload = await queue.get()
        await websocket.send_json(payload)

async def websocket_inbound(queue, chat, users, connected_websockets, user):
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
                markup = await add_chat_message(
                    chat,
                    users,
                    connected_websockets,
                    user,
                    nonce,
                    comment,
                )
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
