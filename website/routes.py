from flask import current_app, render_template, send_from_directory, request, abort, Response, redirect, url_for
from werkzeug import wrap_file
import os
import time
import secrets
import json

import website.chat as chat
import website.viewership as viewership
import website.utils.stream as stream
from website.constants import SEGMENT_INIT, CHAT_SCROLLBACK, BROADCASTER_COLOUR, BROADCASTER_TOKEN, SEGMENTS_DIR, VIEW_COUNTING_PERIOD, HLS_TIME, NOTES, N_NONE
from website.concatenate import ConcatenatedSegments

viewers = viewership.viewers

#When a viewer leaves a comment, they make a POST request to /comment; either
#you can redirect back to /comment-box or you can respond there without
#redirecting. In the second case viewers will get a confirmation dialogue when
#they refresh the page; in the first case, you need to somehow give them the
#note exactly once. That's what this dict is for.
preset_comment_iframe = {}

def new_token():
    return secrets.token_hex(8)

@current_app.route('/')
def index(token=None):
    token = token or request.args.get('token') or request.cookies.get('token') or new_token()
    viewership.setdefault(token)
    response = Response(render_template('index.html', token=token))
    response.set_cookie('token', token)
    return response

@current_app.route('/broadcaster')
@current_app.auth.login_required
def broadcaster():
    return index(token=BROADCASTER_TOKEN)

@current_app.route('/stream.m3u8')
def playlist():
    if not  stream.is_online():
        return abort(404)
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    response = send_from_directory(SEGMENTS_DIR, 'stream.m3u8', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    response.set_cookie('token', token)
    return response

@current_app.route(f'/{SEGMENT_INIT}')
def segment_init():
    if not  stream.is_online():
        return abort(404)
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    response = send_from_directory(SEGMENTS_DIR, f'init.mp4', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route('/stream<int:n>.m4s')
def segment_arbitrary(n):
    if not  stream.is_online():
        return abort(404)
    token = request.args.get('token') or request.cookies.get('token')
    viewership.view_segment(n, token)
    response = send_from_directory(SEGMENTS_DIR, f'stream{n}.m4s', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    if token == None:
        token = new_token()
        response.set_cookie('token', token)
    return response

@current_app.route('/stream.mp4')
def segments():
    if not  stream.is_online():
        return abort(404)
    token = request.cookies.get('token')
    concatenated_segments = ConcatenatedSegments(segments_dir=SEGMENTS_DIR,
                                                 segment_offset=max(VIEW_COUNTING_PERIOD // HLS_TIME, 2),
                                                 stream_timeout=HLS_TIME + 2,
                                                 segment_hook=lambda n: viewership.view_segment(n, token, check_exists=False),
                                                 should_close_connection=lambda: not  stream.is_online())
    file_wrapper = wrap_file(request.environ, concatenated_segments)
    response = Response(file_wrapper, mimetype='video/mp4')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route('/chat')
def chat_iframe():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    messages = (message for message in chat.messages if not message['hidden'])
    messages = zip(messages, range(CHAT_SCROLLBACK)) # show at most CHAT_SCROLLBACK messages
    messages = (message for message, _ in messages)
    return render_template('chat-iframe.html', token=token, messages=messages, broadcaster=token == BROADCASTER_TOKEN, broadcaster_colour=BROADCASTER_COLOUR, debug=request.args.get('debug'))

@current_app.route('/heartbeat')
def heartbeat():
    token = request.args.get('token') or request.cookies.get('token')
    viewership.heartbeat(token)
    online = stream.is_online()
    start_abs, start_rel = stream.get_start(absolute=True, relative=True)
    return {'viewers': viewership.count(),
            'online': online,
            'current_segment': stream.current_segment(),
            'title': stream.get_title(),
            'start_abs': start_abs if online else None,
            'start_rel': start_rel if online else None}

@current_app.route('/comment-box')
def comment_iframe():
    token = request.args.get('token') or request.cookies.get('token') or new_token()

    try:
        preset = preset_comment_iframe.pop(token)
    except KeyError:
        preset = {}
    if preset.get('note', N_NONE) not in NOTES:
        preset['note'] = N_NONE

    captcha = chat.get_captcha(token)

    nickname = viewers[token]['nickname']
    default = viewership.default_nickname(token)
    if nickname == default:
        nickname = ''

    response = render_template('comment-iframe.html',
                               token=token,
                               captcha=captcha,
                               note=NOTES[preset.get('note', N_NONE)],
                               message=preset.get('message', ''),
                               default=default,
                               nickname=nickname,
                               viewer=viewers[token],
                               show_settings=preset.get('show_settings', False))
    response = Response(response)
    response.set_cookie('token', token)
    return response

@current_app.route('/comment', methods=['POST'])
def comment():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    message = request.form.get('message', '').replace('\r', '').replace('\n', ' ').strip()
    c_response = request.form.get('captcha')
    c_token = request.form.get('captcha-token')

    failure_reason = chat.comment(message, token, c_response, c_token)

    # TODO: consider eliminating the POST->GET pattern for speed reasons
    preset_comment_iframe[token] = {'note': failure_reason, 'message': message if failure_reason else ''}
    return redirect(url_for('comment_iframe', token=token))

# TODO: make it so your message that you haven't sent yet stays there when you change your appearance
# ^ This is possible if you use only one form and change buttons to <input type="submit" formaction="/url">
#   BUT then you won't be able to have `required` in any inputs since a message shouldn't be required
#   for changing your appearance. So this is not done for now.
@current_app.route('/settings', methods=['POST'])
def settings():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    nickname = request.form.get('nickname', '')
    password = request.form.get('password', '')

    note, ok = chat.set_nickname(nickname, token)
    if ok:
        if request.form.get('remove-tripcode'):
            note, _ = chat.remove_tripcode(token)
        elif request.form.get('set-tripcode'):
            note, _ = chat.set_tripcode(password, token)

    preset_comment_iframe[token] = {'note': note, 'show_settings': True}
    return redirect(url_for('comment_iframe', token=token))

@current_app.route('/mod', methods=['POST'])
@current_app.auth.login_required
def mod():
    message_ids = request.form.getlist('message_id[]')
    chat.mod(message_ids, request.form.get('hide'), request.form.get('ban'), request.form.get('ban_purge'))
    return f'<meta http-equiv="refresh" content="0;url={url_for("chat_iframe")}"><div style="font-weight:bold;color:white;transform: scaleY(-1);">it is done</div>'

@current_app.route('/stream-info')
def stream_info():
    start_abs, start_rel = stream.get_start(absolute=True, relative=True)
    online =  stream.is_online()
    return render_template('stream-info-iframe.html',
                           title=stream.get_title(),
                           viewer_count=viewership.count(),
                           stream_start_abs_json=json.dumps(start_abs if online else None),
                           stream_start_rel_json=json.dumps(start_rel if online else None),
                           stream_uptime=start_rel if online else None,
                           online=online)

@current_app.route('/teapot')
def teapot():
    return {'short': True, 'stout': True}, 418
