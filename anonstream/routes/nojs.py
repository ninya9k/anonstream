from quart import current_app, request, render_template, redirect, url_for, escape, Markup

from anonstream.captcha import get_random_captcha_digest_for
from anonstream.chat import add_chat_message, Rejected
from anonstream.stream import get_stream_title, get_stream_uptime, get_stream_viewership
from anonstream.user import add_state, pop_state, try_change_appearance, get_users_by_presence, Presence, verify, deverify, BadCaptcha
from anonstream.routes.wrappers import with_user_from, render_template_with_etag
from anonstream.helpers.chat import get_scrollback
from anonstream.helpers.user import get_default_name
from anonstream.utils.chat import generate_nonce
from anonstream.utils.user import concatenate_for_notice

CONFIG = current_app.config
USERS_BY_TOKEN = current_app.users_by_token

@current_app.route('/info.html')
@with_user_from(request)
async def nojs_info(user):
    return await render_template(
        'nojs_info.html',
        user=user,
        viewership=get_stream_viewership(),
        uptime=get_stream_uptime(),
        title=await get_stream_title(),
    )

@current_app.route('/chat/messages.html')
@with_user_from(request)
async def nojs_chat(user):
    return await render_template_with_etag(
        'nojs_chat.html',
        user=user,
        users_by_token=USERS_BY_TOKEN,
        messages=get_scrollback(current_app.messages),
        timeout=CONFIG['THRESHOLD_NOJS_CHAT_TIMEOUT'],
        get_default_name=get_default_name,
    )

@current_app.route('/chat/messages')
@with_user_from(request)
async def nojs_chat_redirect(user):
    return redirect(url_for('nojs_chat', _anchor='end'))

@current_app.route('/chat/users.html')
@with_user_from(request)
async def nojs_users(user):
    users_by_presence = get_users_by_presence()
    return await render_template_with_etag(
        'nojs_users.html',
        user=user,
        get_default_name=get_default_name,
        users_watching=users_by_presence[Presence.WATCHING],
        users_notwatching=users_by_presence[Presence.NOTWATCHING],
        timeout=CONFIG['THRESHOLD_NOJS_CHAT_TIMEOUT'],
    )

@current_app.route('/chat/form.html')
@with_user_from(request)
async def nojs_form(user):
    state_id = request.args.get('state', type=int)
    state = pop_state(user, state_id)
    prefer_chat_form = request.args.get('landing') != 'appearance'
    return await render_template(
        'nojs_form.html',
        user=user,
        state=state,
        prefer_chat_form=prefer_chat_form,
        nonce=generate_nonce(),
        digest=get_random_captcha_digest_for(user),
        default_name=get_default_name(user),
    )

@current_app.post('/chat/form')
@with_user_from(request)
async def nojs_form_redirect(user):
    comment = (await request.form).get('comment', '')
    if len(comment) > CONFIG['CHAT_COMMENT_MAX_LENGTH']:
        comment = ''

    if comment:
        state_id = add_state(user, comment=comment)
    else:
        state_id = None

    return redirect(url_for('nojs_form', state=state_id))

@current_app.post('/chat/message')
@with_user_from(request)
async def nojs_submit_message(user):
    form = await request.form

    comment = form.get('comment', '')
    digest = form.get('captcha-digest', '')
    answer = form.get('captcha-answer', '')
    try:
        verification_happened = verify(user, digest, answer)
    except BadCaptcha as e:
        notice, *_ = e.args
        state_id = add_state(user, notice=notice, comment=comment)
    else:
        nonce = form.get('nonce', '')
        try:
            # If the comment is empty but the captcha was just solved,
            # be lenient: don't raise an exception and don't create a notice
            add_chat_message(
                user,
                nonce,
                comment,
                ignore_empty=verification_happened,
            )
        except Rejected as e:
            notice, *_ = e.args
            state_id = add_state(user, notice=notice, comment=comment)
        else:
            deverify(user)
            state_id = None

    return redirect(url_for(
        'nojs_form',
        token=user['token'],
        landing='chat',
        state=state_id,
    ))

@current_app.post('/chat/appearance')
@with_user_from(request)
async def nojs_submit_appearance(user):
    form = await request.form

    # Collect form data
    name = form.get('name', '').strip()
    if len(name) == 0 or name == get_default_name(user):
        name = None

    color = form.get('color', '')
    password = form.get('password', '')

    if form.get('clear-tripcode', type=bool):
        want_tripcode = False
    elif form.get('set-tripcode', type=bool):
        want_tripcode = True
    else:
        want_tripcode = None

    # Change appearance (iff form data was good)
    errors = try_change_appearance(user, name, color, password, want_tripcode)
    if errors:
        notice = Markup('<br>').join(
            concatenate_for_notice(*error.args) for error in errors
        )
    else:
        notice = 'Changed appearance'

    state_id = add_state(user, notice=notice, verbose=len(errors) > 1)
    return redirect(url_for(
        'nojs_form',
        token=user['token'],
        landing='appearance' if errors else 'chat',
        state=state_id,
    ))
