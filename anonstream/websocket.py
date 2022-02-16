import asyncio

from quart import websocket

from anonstream.stream import get_stream_title, get_stream_uptime
from anonstream.chat import broadcast, add_chat_message, Rejected
from anonstream.users import is_present, users_for_websocket, see
from anonstream.wrappers import with_first_argument
from anonstream.utils import listmap
from anonstream.utils.chat import generate_nonce, message_for_websocket
from anonstream.utils.websocket import parse_websocket_data, Malformed

async def websocket_outbound(queue, messages, users, default_host_name, default_anon_name):
    payload = {
        'type': 'init',
        'nonce': generate_nonce(),
        'title': get_stream_title(),
        'uptime': get_stream_uptime(),
        'chat': listmap(
            with_first_argument(users)(message_for_websocket),
            messages,
        ),
        'users': users_for_websocket(messages, users),
        'default': {True: default_host_name, False: default_anon_name},
    }
    await websocket.send_json(payload)
    while True:
        payload = await queue.get()
        await websocket.send_json(payload)

async def websocket_inbound(queue, chat, users, connected_websockets, user, secret):
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
                    secret,
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
