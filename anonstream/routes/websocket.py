import asyncio

from quart import current_app, websocket

from anonstream.websocket import websocket_outbound, websocket_inbound
from anonstream.routes.wrappers import with_user_from

@current_app.websocket('/live')
@with_user_from(websocket)
async def live(user):
    queue = asyncio.Queue()
    current_app.websockets.add(queue)

    producer = websocket_outbound(
        queue=queue,
        messages=current_app.chat['messages'].values(),
        users=current_app.users,
    )
    consumer = websocket_inbound(
        queue=queue,
        chat=current_app.chat,
        users=current_app.users,
        connected_websockets=current_app.websockets,
        user=user,
    )
    try:
        await asyncio.gather(producer, consumer)
    finally:
        current_app.websockets.remove(queue)
