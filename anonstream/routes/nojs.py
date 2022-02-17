from quart import current_app, request, render_template, redirect, url_for

from anonstream.stream import get_stream_title
from anonstream.user import add_notice, pop_notice
from anonstream.chat import add_chat_message, Rejected
from anonstream.routes.wrappers import with_user_from
from anonstream.helpers.user import get_default_name
from anonstream.utils.chat import generate_nonce

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
    return await render_template(
        'nojs_chat.html',
        user=user,
        users=current_app.users,
        messages=current_app.chat['messages'].values(),
        get_default_name=get_default_name,
    )

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
        await add_chat_message(
            chat=current_app.chat,
            users=current_app.users,
            websockets=current_app.websockets,
            user=user,
            nonce=nonce,
            comment=comment,
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
