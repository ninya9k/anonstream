import asyncio

from quart import current_app, request, render_template, make_response, redirect, websocket, url_for

from anonstream.stream import get_stream_title
from anonstream.segments import CatSegments, Offline
from anonstream.users import get_default_name, add_notice, pop_notice
from anonstream.wrappers import with_user_from, auth_required
from anonstream.websocket import websocket_outbound, websocket_inbound
from anonstream.chat import add_chat_message, Rejected
from anonstream.utils.chat import create_message, generate_nonce, NonceReuse

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
    notice_id = request.args.get('notice', type=int)
    prefer_chat_form = request.args.get('landing') != 'appearance'
    return await render_template(
        'nojs_form.html',
        user=user,
        notice=pop_notice(user, notice_id),
        prefer_chat_form=prefer_chat_form,
        nonce=generate_nonce(),
        default_name=get_default_name(user),
    )

@current_app.post('/chat/message')
@with_user_from(request)
async def nojs_submit_message(user):
    form = await request.form
    comment = form.get('comment', '')
    nonce = form.get('nonce', '')

    try:
        message_id, _, _ = create_message(
            message_ids=current_app.chat.keys(),
            secret=current_app.config['SECRET_KEY'],
            nonce=nonce,
            comment=comment,
        )
    except NonceReuse:
        notice_id = add_notice(user, 'Discarded suspected duplicate message')
    else:
        try:
            await add_chat_message(
                current_app.chat,
                current_app.websockets,
                user['token'],
                message_id,
                comment
            )
        except Rejected as e:
            notice, *_ = e.args
            notice_id = add_notice(user, notice)
        else:
            notice_id = None

    return redirect(url_for('nojs_form', token=user['token'], notice=notice_id))

@current_app.post('/chat/appearance')
@with_user_from(request)
async def nojs_submit_appearance(user):
    pass
