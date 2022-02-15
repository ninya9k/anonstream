import asyncio

from quart import websocket

from anonstream.stream import get_stream_title, get_stream_uptime
from anonstream.chat import broadcast, add_chat_message, Rejected
from anonstream.utils.chat import generate_nonce
from anonstream.utils.websocket import parse_websocket_data

async def websocket_outbound(queue):
    payload = {
        'type': 'init',
        'nonce': generate_nonce(),
        'title': get_stream_title(),
        'uptime': get_stream_uptime(),
        'chat': [],
    }
    await websocket.send_json(payload)
    while True:
        payload = await queue.get()
        await websocket.send_json(payload)

async def websocket_inbound(queue, connected_websockets, token, secret, chat):
    while True:
        receipt = await websocket.receive_json()
        try:
            message_id, nonce, comment = parse_websocket_data(chat.keys(), secret, receipt)
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
                    connected_websockets,
                    token,
                    message_id,
                    comment
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
