# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

from quart import current_app, request, render_template, redirect, url_for, escape, Markup

from anonstream.captcha import get_random_captcha_digest_for
from anonstream.chat import add_chat_message, Rejected
from anonstream.stream import is_online, get_stream_title, get_stream_uptime_and_viewership
from anonstream.user import add_state, pop_state, try_change_appearance, update_presence, get_users_by_presence, Presence, verify, deverify, BadCaptcha, reading
from anonstream.routes.wrappers import with_user_from, render_template_with_etag
from anonstream.helpers.chat import get_scrollback
from anonstream.helpers.user import get_default_name
from anonstream.utils.chat import generate_nonce, escape_css_string, get_emotehash
from anonstream.utils.security import generate_csp
from anonstream.utils.user import concatenate_for_notice

CONFIG = current_app.config
USERS_BY_TOKEN = current_app.users_by_token
EMOTES = current_app.emotes

@current_app.route('/stream.html')
@with_user_from(request)
async def nojs_stream(timestamp, user):
    return await render_template(
        'nojs_stream.html',
        csp=generate_csp(),
        user=user,
        online=is_online(),
    )

@current_app.route('/info.html')
@with_user_from(request)
async def nojs_info(timestamp, user):
    update_presence(user)
    uptime, viewership = get_stream_uptime_and_viewership()
    return await render_template(
        'nojs_info.html',
        csp=generate_csp(),
        refresh=CONFIG['NOJS_REFRESH_INFO'],
        user=user,
        viewership=viewership,
        uptime=uptime,
        title=await get_stream_title(),
        Presence=Presence,
    )

@current_app.route('/chat/messages.html')
@with_user_from(request)
async def nojs_chat_messages(timestamp, user):
    reading(user)
    return await render_template_with_etag(
        'nojs_chat_messages.html',
        {'csp': generate_csp()},
        refresh=CONFIG['NOJS_REFRESH_MESSAGES'],
        user=user,
        users_by_token=USERS_BY_TOKEN,
        emotes=EMOTES,
        emotesheet=CONFIG['EMOTE_SHEET'],
        emotehash=get_emotehash(tuple(EMOTES)),
        messages=get_scrollback(current_app.messages),
        timeout=CONFIG['NOJS_TIMEOUT_CHAT'],
        escape_css_string=escape_css_string,
        get_default_name=get_default_name,
    )

@current_app.route('/chat/messages')
@with_user_from(request)
async def nojs_chat_messages_redirect(timestamp, user):
    url = url_for('nojs_chat_messages', token=user['token'], _anchor='end')
    return redirect(url, 303)

@current_app.route('/chat/users.html')
@with_user_from(request)
async def nojs_chat_users(timestamp, user):
    users_by_presence = get_users_by_presence()
    return await render_template_with_etag(
        'nojs_chat_users.html',
        {'csp': generate_csp()},
        refresh=CONFIG['NOJS_REFRESH_USERS'],
        user=user,
        get_default_name=get_default_name,
        users_watching=users_by_presence[Presence.WATCHING],
        users_notwatching=users_by_presence[Presence.NOTWATCHING],
        timeout=CONFIG['NOJS_TIMEOUT_CHAT'],
    )

@current_app.route('/chat/form.html')
@with_user_from(request)
async def nojs_chat_form(timestamp, user):
    state_id = request.args.get('state', type=int)
    state = pop_state(user, state_id)
    prefer_chat_form = request.args.get('landing') != 'appearance'
    return await render_template(
        'nojs_chat_form.html',
        csp=generate_csp(),
        user=user,
        state=state,
        prefer_chat_form=prefer_chat_form,
        nonce=generate_nonce(),
        digest=get_random_captcha_digest_for(user),
        default_name=get_default_name(user),
        max_comment_length=CONFIG['CHAT_COMMENT_MAX_LENGTH'],
        max_name_length=CONFIG['CHAT_NAME_MAX_LENGTH'],
        max_password_length=CONFIG['CHAT_TRIPCODE_PASSWORD_MAX_LENGTH'],
    )

@current_app.post('/chat/form')
@with_user_from(request)
async def nojs_chat_form_redirect(timestamp, user):
    comment = (await request.form).get('comment', '')
    if comment:
        state_id = add_state(
            user,
            comment=comment[:CONFIG['CHAT_COMMENT_MAX_LENGTH']],
        )
    else:
        state_id = None
    url = url_for('nojs_chat_form', token=user['token'], state=state_id)
    return redirect(url, 303)

@current_app.post('/chat/message')
@with_user_from(request)
async def nojs_submit_message(timestamp, user):
    form = await request.form

    comment = form.get('comment', '')
    digest = form.get('captcha-digest', '')
    answer = form.get('captcha-answer', '')
    try:
        verification_happened = verify(user, digest, answer)
    except BadCaptcha as e:
        notice, *_ = e.args
        state_id = add_state(
            user,
            notice=notice,
            comment=comment[:CONFIG['CHAT_COMMENT_MAX_LENGTH']],
        )
    else:
        nonce = form.get('nonce', '')
        try:
            # If the comment is empty but the captcha was just solved,
            # be lenient: don't raise an exception and don't create a notice
            message_was_added = add_chat_message(
                user,
                nonce,
                comment,
                ignore_empty=verification_happened,
            )
        except Rejected as e:
            notice, *_ = e.args
            state_id = add_state(
                user,
                notice=notice,
                comment=comment[:CONFIG['CHAT_COMMENT_MAX_LENGTH']],
            )
        else:
            state_id = None
            if message_was_added:
                deverify(user, timestamp=timestamp)

    url = url_for(
        'nojs_chat_form',
        token=user['token'],
        landing='chat',
        state=state_id,
    )
    return redirect(url, 303)

@current_app.post('/chat/appearance')
@with_user_from(request)
async def nojs_submit_appearance(timestamp, user):
    form = await request.form

    # Collect form data
    name = form.get('name', '').strip()
    if len(name) == 0:
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
    url = url_for(
        'nojs_chat_form',
        token=user['token'],
        landing='appearance' if errors else 'chat',
        state=state_id,
    )
    return redirect(url, 303)
