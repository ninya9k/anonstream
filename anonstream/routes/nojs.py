from quart import current_app, request, render_template, redirect, url_for, escape, Markup

from anonstream.stream import get_stream_title
from anonstream.user import add_notice, pop_notice, try_change_appearance
from anonstream.chat import add_chat_message, Rejected
from anonstream.routes.wrappers import with_user_from, render_template_with_etag
from anonstream.helpers.user import get_default_name
from anonstream.helpers.chat import get_scrollback
from anonstream.utils.chat import generate_nonce
from anonstream.utils.user import concatenate_for_notice

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
    return await render_template_with_etag(
        'nojs_chat.html',
        user=user,
        users_by_token=current_app.users_by_token,
        messages=get_scrollback(current_app.messages),
        timeout=current_app.config['THRESHOLD_NOJS_CHAT_TIMEOUT'],
        get_default_name=get_default_name,
    )

@current_app.route('/chat/redirect')
@with_user_from(request)
async def nojs_chat_redirect(user):
    return redirect(url_for('nojs_chat', _anchor='end'))

@current_app.route('/chat/form.html')
@with_user_from(request)
async def nojs_form(user):
    notice_id = request.args.get('notice', type=int)
    notice, verbose = pop_notice(user, notice_id)
    prefer_chat_form = request.args.get('landing') != 'appearance'
    return await render_template(
        'nojs_form.html',
        user=user,
        notice=notice,
        verbose=verbose,
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
        add_chat_message(user, nonce, comment)
    except Rejected as e:
        notice, *_ = e.args
        notice_id = add_notice(user, notice)
    else:
        notice_id = None

    return redirect(url_for('nojs_form', token=user['token'], landing='chat', notice=notice_id))

@current_app.post('/chat/appearance')
@with_user_from(request)
async def nojs_submit_appearance(user):
    form = await request.form
    name = form.get('name', '') or None
    color = form.get('color', '')
    password = form.get('password', '')
    want_delete_tripcode = form.get('clear-tripcode', type=bool)
    want_change_tripcode = form.get('set-tripcode', type=bool)

    errors = try_change_appearance(
        user,
        name,
        color,
        password,
        want_delete_tripcode,
        want_change_tripcode,
    )
    if errors:
        notice = Markup('<br>').join(
            concatenate_for_notice(*error.args) for error in errors
        )
    else:
        notice = 'Changed appearance'

    notice_id = add_notice(user, notice, verbose=len(errors) > 1)
    return redirect(url_for(
        'nojs_form',
        token=user['token'],
        landing='appearance' if errors else 'chat',
        notice=notice_id,
    ))
