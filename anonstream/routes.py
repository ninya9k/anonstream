import asyncio

from quart import current_app, request, render_template, make_response, redirect, websocket

from anonstream.stream import get_stream_title
from anonstream.segments import CatSegments, Offline
from anonstream.users import get_default_name
from anonstream.wrappers import with_user_from, auth_required
from anonstream.websocket import websocket_outbound, websocket_inbound

@current_app.route('/')
@with_user_from(request)
async def home(user):
    return await render_template('home.html', user=user)

@current_app.route('/stream.mp4')
@with_user_from(request)
async def stream(user):
    try:
        cat_segments = CatSegments(
            directory_cache=current_app.segments_directory_cache,
            token=user['token']
        )
    except Offline:
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
@with_user_from(websocket)
async def live(user):
    queue = asyncio.Queue()
    current_app.websockets.add(queue)

    producer = websocket_outbound(queue)
    consumer = websocket_inbound(
        queue=queue,
        connected_websockets=current_app.websockets,
        token=user['token'],
        secret=current_app.config['SECRET_KEY'],
        chat=current_app.chat,
    )
    try:
        await asyncio.gather(producer, consumer)
    finally:
        current_app.websockets.remove(queue)

@current_app.route('/info.html')
@with_user_from(request)
async def nojs_info(user):
    return await render_template(
        'nojs_info.html',
        user=user,
        title=get_stream_title(),
    )

@current_app.route('/chat/messages.html')
@with_user_from(request)
async def nojs_chat(user):
    return await render_template('nojs_chat.html', user=user)

@current_app.route('/chat/form.html')
@with_user_from(request)
async def nojs_form(user):
    return await render_template(
        'nojs_form.html',
        user=user,
        default_name=get_default_name(user),
    )
