import asyncio

from quart import websocket

from anonstream.stream import get_stream_title, get_stream_uptime
from anonstream.chat import add_chat_message
from anonstream.utils.chat import generate_nonce
from anonstream.utils.websocket import parse

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
        receipt, error = parse(chat.keys(), secret, receipt)
        if error is not None:
            payload = {
                'type': 'error',
                'because': error,
            }
        else:
            text, nonce, message_id = receipt
            add_chat_message(chat, message_id, token, text)
            payload = {
                'type': 'ack',
                'nonce': nonce,
                'next': generate_nonce(),
            }
        await queue.put(payload)

        if error is None:
            payload = {
                'type': 'chat',
                'color': '#c7007f',
                'name': 'Anonymous',
                'text': text,
            }
            for other_queue in connected_websockets:
                await other_queue.put(payload)
