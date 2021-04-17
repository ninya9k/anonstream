from flask import current_app, render_template, send_from_directory, request, abort, Response, redirect, url_for
from werkzeug import wrap_file
import os
import time
import secrets
import json
import datetime

import website.chat as chat
import website.viewership as viewership
import website.utils.stream as stream
from website.constants import DIR_STATIC, DIR_STATIC_EXTERNAL, SEGMENT_INIT, CHAT_SCROLLBACK, BROADCASTER_COLOUR, BROADCASTER_TOKEN, SEGMENTS_DIR, VIEW_COUNTING_PERIOD, HLS_TIME, NOTES, N_NONE
from website.concatenate import ConcatenatedSegments, resolve_segment_offset

viewers = viewership.viewers

def new_token():
    return secrets.token_hex(8)

def get_token(form=False):
    token = (request.form if form else request.args).get('token')
    if token == None or len(token) >= 256 or len(token) < 4:
        token = request.cookies.get('token')
    if token and (len(token) >= 256 or len(token) < 4):
        token = None
    return token

@current_app.route('/')
def index(token=None):
    token = token or get_token() or new_token()
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass
    use_videojs = bool(request.args.get('videojs', default=1, type=int))
    viewership.made_request(token)

    response = render_template('index.html',
                               token=token,
                               use_videojs=use_videojs,
                               start_number=resolve_segment_offset() if stream.is_online() else 0)
    response = Response(response) # TODO: add a view of the chat only, either as an arg here or another route
    response.set_cookie('token', token)
    return response

@current_app.route('/broadcaster')
@current_app.auth.login_required
def broadcaster():
    return index(token=BROADCASTER_TOKEN)

## simple version, just reads the file from disk
#@current_app.route('/stream.m3u8')
#def playlist():
#    if not stream.is_online():
#        return abort(404)
#
#    token = get_token() or new_token()
#    try:
#        viewership.video_was_corrupted.remove(token)
#    except KeyError:
#        pass
#    response = send_from_directory(SEGMENTS_DIR, 'stream.m3u8', add_etags=False)
#    response.headers['Cache-Control'] = 'no-cache'
#    response.set_cookie('token', token)
#    return response

@current_app.route('/stream.m3u8')
def playlist():
    if not stream.is_online():
        return abort(404)
    token = get_token()
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass

    try:
        file_wrapper = wrap_file(request.environ, stream.TokenPlaylist(token))
    except FileNotFoundError:
        return abort(404)
    response = Response(file_wrapper, mimetype='application/x-mpegURL')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route(f'/{SEGMENT_INIT}')
def segment_init():
    if not stream.is_online():
        return abort(404)

    token = get_token() or new_token()
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass
    response = send_from_directory(SEGMENTS_DIR, f'init.mp4', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    response.set_cookie('token', token)
    return response

@current_app.route('/stream<int:n>.m4s')
def segment_arbitrary(n):
    if not stream.is_online():
        return abort(404)

    token = get_token()
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass
    viewership.view_segment(n, token)
    response = send_from_directory(SEGMENTS_DIR, f'stream{n}.m4s', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route('/stream.mp4')
def segments():
    if not stream.is_online():
        return abort(404)
    token = get_token() or new_token()
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass

    start_number = request.args.get('segment', type=int) if 'segment' in request.args else resolve_segment_offset()

    try:
        concatenated_segments = ConcatenatedSegments(start_number=start_number,
                                                     segment_hook=lambda n: viewership.view_segment(n, token, check_exists=False),
                                                     corrupt_hook=lambda: viewership.video_was_corrupted.add(token), # lock?
                                                     should_close_connection=lambda: not stream.is_online())
    except FileNotFoundError:
        return abort(404)

    file_wrapper = wrap_file(request.environ, concatenated_segments)
    response = Response(file_wrapper, mimetype='video/mp4')
    response.headers['Cache-Control'] = 'no-store'
    response.set_cookie('token', token)
    return response

@current_app.route('/chat')
def chat_iframe():
    token = get_token()
    viewership.made_request(token)

    include_user_list = bool(request.args.get('users', default=1, type=int))
    messages = (message for message in chat.messages if not message['hidden'])
    messages = zip(messages, range(CHAT_SCROLLBACK)) # show at most CHAT_SCROLLBACK messages
    messages = (message for message, _ in messages)
    return render_template('chat-iframe.html',
                           token=token,
                           messages=messages,
                           include_user_list=include_user_list,
                           people=viewership.get_people_list(),
                           default_nickname=viewership.default_nickname,
                           broadcaster=token == BROADCASTER_TOKEN,
                           broadcaster_colour=BROADCASTER_COLOUR,
                           debug=request.args.get('debug'),
                           len=len)

@current_app.route('/heartbeat')
def heartbeat():
    token = get_token()
    viewership.made_request(token)
    online = stream.is_online()
    start_abs, start_rel = stream.get_start(absolute=True, relative=True)

    response =  {'viewers': viewership.count(),
                 'online': online,
                 'current_segment': stream.current_segment(),
                 'title': stream.get_title(),
                 'start_abs': start_abs if online else None,
                 'start_rel': start_rel if online else None}
    if token in viewership.video_was_corrupted:
        response['corrupted'] = True

    return response

@current_app.route('/comment-box')
def comment_iframe(token=None):
    token = token or get_token() or new_token()
    viewership.made_request(token)

    try:
        preset = viewership.preset_comment_iframe.pop(token)
    except KeyError:
        preset = {}
    if preset.get('note', N_NONE) not in NOTES:
        preset['note'] = N_NONE

    captcha = chat.get_captcha(token)

    response = render_template('comment-iframe.html',
                               token=token,
                               captcha=captcha,
                               nonce=chat.new_nonce(),
                               note=NOTES[preset.get('note', N_NONE)],
                               message=preset.get('message', ''),
                               default=viewership.default_nickname(token),
                               nickname=viewers[token]['nickname'],
                               viewer=viewers[token],
                               show_settings=preset.get('show_settings', False))
    response = Response(response)
    response.set_cookie('token', token)
    return response

@current_app.route('/comment', methods=['POST'])
def comment():
    token = get_token(form=True) or new_token()
    nonce = request.form.get('nonce')
    message = request.form.get('message', '').replace('\r', '').replace('\n', ' ').strip()
    c_response = request.form.get('captcha')
    c_token = request.form.get('captcha-token')

    viewership.made_request(token)

    failure_reason = chat.comment(message, token, c_response, c_token, nonce)

    viewership.preset_comment_iframe[token] = {'note': failure_reason, 'message': message if failure_reason else ''}
    return comment_iframe(token=token)

# TODO: make it so your message that you haven't sent yet stays there when you change your appearance
# ^ This is possible if you use only one form and change buttons to <input type="submit" formaction="/url">
#   BUT then you won't be able to have `required` in any inputs since a message shouldn't be required
#   for changing your appearance. So this is not done for now.
@current_app.route('/settings', methods=['POST'])
def settings():
    token = get_token(form=True) or new_token()
    nickname = request.form.get('nickname', '')
    password = request.form.get('password', '')

    viewership.made_request(token)

    note, ok = chat.set_nickname(nickname, token)
    if ok:
        if request.form.get('remove-tripcode'):
            note, _ = chat.remove_tripcode(token)
        elif request.form.get('set-tripcode'):
            note, _ = chat.set_tripcode(password, token)

    viewership.preset_comment_iframe[token] = {'note': note, 'show_settings': True}
    return redirect(url_for('comment_iframe', token=token))

# TODO: undo hides; optionally show that a comment was hidden; optionally show bans in chat
@current_app.route('/mod/chat', methods=['POST'])
@current_app.auth.login_required
def mod_chat():
    message_ids = request.form.getlist('message_id[]')
    chat.mod_chat(message_ids, request.form.get('hide'), request.form.get('ban'), request.form.get('ban_purge'))
    return f'<meta http-equiv="refresh" content="0;url={url_for("chat_iframe")}"><div style="font-weight:bold;color:white;transform: scaleY(-1);">it is done</div>'

@current_app.route('/mod/users', methods=['POST'])
@current_app.auth.login_required
def mod_users():
    tokens = request.form.getlist('token[]')
    banned = bool(request.form.get('banned', type=int))
    chat.mod_users(tokens, banned=banned)

    noscript = bool(request.form.get('noscript', type=int))
    return f'<meta http-equiv="refresh" content="0;url={url_for("users") if noscript else url_for("chat_iframe")}"><div style="font-weight:bold;color:white;">it is done</div>'

# TODO: "you're not receiving the stream" message if that token isn't receiving the stream; make sure they don't see it when they first load the page
@current_app.route('/stream-info')
def stream_info():
    token = get_token() or new_token()
    embed_images = bool(request.args.get('embed', type=int))

    viewership.made_request(token)

    start_abs, start_rel = stream.get_start(absolute=True, relative=True)
    online = stream.is_online()
    return render_template('stream-info-iframe.html',
                           title=stream.get_title(),
                           viewer_count=viewership.count(),
                           stream_start_abs_json=json.dumps(start_abs if online else None),
                           stream_start_rel_json=json.dumps(start_rel if online else None),
                           stream_uptime=start_rel if online else None,
                           online=online,
                           video_was_corrupted=token != None and token in viewership.video_was_corrupted,
                           embed_images=embed_images,
                           token=token,
                           broadcaster_colour=BROADCASTER_COLOUR)

@current_app.route('/users')
def users():
    token = get_token()
    viewership.made_request(token)
    return render_template('users-iframe.html',
                           token=token,
                           people=viewership.get_people_list(),
                           default_nickname=viewership.default_nickname,
                           broadcaster=token == BROADCASTER_TOKEN,
                           debug=request.args.get('debug'),
                           broadcaster_colour=BROADCASTER_COLOUR,
                           len=len)

@current_app.route('/static/radial.apng')
def radial():
    response = send_from_directory(DIR_STATIC, 'radial.apng', mimetype='image/png', add_etags=False)
    response.headers['Cache-Control'] = 'no-store' # caching this in any way messes with the animation
    response.expires = response.date
    return response

@current_app.route('/static/<fn>')
def _static(fn):
    response = send_from_directory(DIR_STATIC, fn, add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route('/static/external/<fn>')
def third_party(fn):
    response = send_from_directory(DIR_STATIC_EXTERNAL, fn, add_etags=False)
    response.headers['Cache-Control'] = 'public, max-age=604800, immutable'
    response.expires = response.date + datetime.timedelta(days=7)
    return response

@current_app.after_request
def add_header(response):
    try:
        response.headers.pop('Last-Modified')
    except KeyError:
        pass
    return response

@current_app.route('/teapot')
def teapot():
    return {'short': True, 'stout': True}, 418
