import asyncio

from quart import current_app, request, render_template, make_response, redirect, websocket

from anonstream.segments import CatSegments
from anonstream.wrappers import with_token_from, auth_required
from anonstream.websocket import websocket_outbound, websocket_inbound

@current_app.route('/')
@with_token_from(request)
async def home(token):
    return await render_template('home.html', token=token)

@current_app.route('/stream.mp4')
@with_token_from(request)
async def stream(token):
    try:
        cat_segments = CatSegments(current_app.segments_directory_cache, token)
    except ValueError:
        return 'offline', 404
    response = await make_response(cat_segments.stream())
    response.headers['Content-Type'] = 'video/mp4'
    response.timeout = None
    return response

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
        connected_websockets=current_app.websockets,
        token=token,
        secret=current_app.config['SECRET_KEY'],
        chat=current_app.chat,
    )
    try:
        await asyncio.gather(producer, consumer)
    finally:
        current_app.websockets.pop(token)
