import asyncio

from quart import current_app, request, render_template, redirect, websocket

from anonstream.wrappers import with_token_from, auth_required
from anonstream.websocket import websocket_outbound, websocket_inbound

@current_app.route('/')
@with_token_from(request)
async def home(token):
    return await render_template('home.html', token=token)

@current_app.route('/login')
@auth_required
async def login():
    return redirect('/')

@current_app.websocket('/live')
@with_token_from(websocket)
async def live(token):
    queue = asyncio.Queue()
    current_app.websockets[token] = queue

    producer = websocket_outbound(queue)
    consumer = websocket_inbound(
        secret=current_app.config['SECRET_KEY'],
        connected_websockets=current_app.websockets,
        chat=current_app.chat,
        token=token,
    )
    try:
        await asyncio.gather(producer, consumer)
    finally:
        current_app.websockets.pop(token)
