from flask import current_app, render_template, send_from_directory, request, abort, redirect, url_for, make_response, send_file
from werkzeug import wrap_file
import os
import time
import secrets
import json
import datetime
import re
import toml

import website.chat as chat
import website.viewership as viewership
import website.utils.stream as stream
from website.constants import DIR_STATIC, DIR_STATIC_EXTERNAL, VIDEOJS_ENABLED_BY_DEFAULT, SEGMENT_INIT, CHAT_SCROLLBACK, BROADCASTER_COLOUR, BROADCASTER_TOKEN, SEGMENTS_DIR, VIEW_COUNTING_PERIOD, CONFIG, CONFIG_FILE, NOTES, N_NONE, MESSAGE_MAX_LENGTH, BACKGROUND_COLOUR
from website.concatenate import ConcatenatedSegments, resolve_segment_offset

RE_WHITESPACE = re.compile(r'\s+')

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

@current_app.route('/', methods=['GET', 'POST'])
def index(token=None):
    token = token or get_token() or new_token()
    viewership.made_request(token)
    if request.method == 'POST':
        password = request.form.get('password', '')
        chat.set_tripcode(password, token)
    if not viewership.is_allowed(token):
        response = render_template('secret-club.html', token=token, tripcode=viewers[token]['tripcode'])
        response = make_response(response, 403)
        response.set_cookie('token', token)
        return response
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass

    use_videojs = bool(request.args.get('videojs', default=int(VIDEOJS_ENABLED_BY_DEFAULT), type=int))
    online = stream.is_online()

    response = render_template('index.html',
                               token=token,
                               use_videojs=use_videojs,
                               online=online,
                               start_number=resolve_segment_offset() if online else 0,
                               hls_time=CONFIG['stream']['hls_time'])
    response = make_response(response) # TODO: add a view of the chat only, either as an arg here or another route
    response.set_cookie('token', token)
    return response

@current_app.route('/broadcaster')
@current_app.auth.login_required
def broadcaster():
    return index(token=BROADCASTER_TOKEN)

@current_app.route('/stream.m3u8')
def playlist():
    if not stream.is_online():
        return abort(404)
    token = get_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass

    try:
        token_playlist = stream.token_playlist(token)
    except FileNotFoundError:
        return abort(404)
    response = make_response(token_playlist)
    response.mimetype = 'application/x-mpegURL'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route(f'/{SEGMENT_INIT}')
def segment_init():
    if not stream.is_online():
        return abort(404)
    token = get_token() or new_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)
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
    if not viewership.is_allowed(token):
        return abort(403)
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass

    # only send segments that are listed in stream.m3u8
    # this stops old segments from previous streams being sent
    if f'stream{n}.m4s' not in stream.get_segments():
        return abort(404)
    viewership.view_segment(n, token)
    response = send_from_directory(SEGMENTS_DIR, f'stream{n}.m4s', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route('/stream.mp4')
def segments():
    if not stream.is_online():
        return abort(404)
    token = get_token() or new_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)
    try:
        viewership.video_was_corrupted.remove(token)
    except KeyError:
        pass

    def should_close_connection():
        if not stream.is_online():
            return True
        if not viewership.is_allowed(token):
            return True
        return False

    start_number = request.args.get('segment', type=int)
    if start_number == None:
        start_number = resolve_segment_offset()
    try:
        concatenated_segments = ConcatenatedSegments(start_number=start_number,
                                                     segment_hook=lambda n: viewership.view_segment(n, token, check_exists=False),
                                                     corrupt_hook=lambda: viewership.video_was_corrupted.add(token), # lock?
                                                     should_close_connection=should_close_connection)
    except FileNotFoundError:
        return abort(404)

    def generate():
        while True:
            chunk = concatenated_segments.read(8192)
            if chunk == b'':
                return
            yield chunk
    response = current_app.response_class(generate(), mimetype='video/mp4')
    response.headers['Cache-Control'] = 'no-store'
    response.set_cookie('token', token)
    return response

@current_app.route('/chat')
def chat_iframe():
    token = get_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)

    include_user_list = bool(request.args.get('users', default=1, type=int))
    with viewership.lock: # required because another thread can change chat.messages while we're iterating through it
        messages = (message for message in chat.messages if not message['hidden'])
        messages = zip(messages, range(CHAT_SCROLLBACK)) # show at most CHAT_SCROLLBACK messages
        messages = [message for message, _ in messages]

    chat.decorate(messages)
    return render_template('chat-iframe.html',
                           token=token,
                           messages=messages,
                           include_user_list=include_user_list,
                           people=viewership.get_people_list(),
                           default_nickname=viewership.default_nickname,
                           broadcaster=token == BROADCASTER_TOKEN,
                           broadcaster_colour=BROADCASTER_COLOUR,
                           background_colour=BACKGROUND_COLOUR,
                           stream_title=stream.get_title(),
                           stream_viewers=viewership.count(),
                           stream_uptime=stream.readable_uptime(),
                           debug=request.args.get('debug'),
                           RE_WHITESPACE=RE_WHITESPACE,
                           len=len,
                           chr=chr)

@current_app.route('/heartbeat')
def heartbeat():
    token = get_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)
    online = stream.is_online()
    start_abs, start_rel = stream.get_start(absolute=True, relative=True)

    response =  {'viewers': viewership.count(),
                 'online': online,
                 'current_segment': stream.current_segment(),
                 'title': stream.get_title(),
                 'start_abs': start_abs if online else None,
                 'start_rel': start_rel if online else None}
    # commented out because we should be able to tell if we're not receiving the stream already
#    if token in viewership.video_was_corrupted:
#        response['corrupted'] = True

    return response

@current_app.route('/comment-box', methods=['GET', 'POST'])
def comment_iframe(token=None):
    token = token or get_token() or new_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)

    try:
        preset = viewership.preset_comment_iframe.pop(token)
    except KeyError:
        preset = {}

    # a new captcha was requested; fill in the message that the user has typed so far
    if preset == {} and request.method == 'POST':
        message = request.form.get('message', '')
        if len(message) < MESSAGE_MAX_LENGTH:
            preset['message'] = message

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
    response = make_response(response)
    response.set_cookie('token', token)
    return response

@current_app.route('/comment', methods=['POST'])
def comment():
    token = get_token(form=True) or new_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)

    nonce = request.form.get('nonce')
    message = request.form.get('message', '').replace('\r', '').replace('\n', ' ').strip()
    c_response = request.form.get('captcha')
    c_ciphertext = request.form.get('captcha-ciphertext')

    failure_reason = chat.comment(message, token, c_response, c_ciphertext, nonce)

    viewership.preset_comment_iframe[token] = {'note': failure_reason, 'message': message if failure_reason else ''}
    return comment_iframe(token=token)

# TODO: make it so your message that you haven't sent yet stays there when you change your appearance
# ^ This is possible if you use only one form and change buttons to <input type="submit" formaction="/url">
#   BUT it's not easy to make sure the formaction is correct when you press enter in any given <input>.
#   There could be some other way, idk.
@current_app.route('/settings', methods=['POST'])
def settings():
    token = get_token(form=True) or new_token()
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)

    nickname = request.form.get('nickname', '')
    password = request.form.get('password', '')

    old_nickname = viewers[token]['nickname']
    old_tripcode = viewers[token]['tripcode']

    note, ok = chat.set_nickname(nickname, token)
    if ok:
        if request.form.get('remove-tripcode'):
            note, _ = chat.remove_tripcode(token)
        elif request.form.get('set-tripcode'):
            note, _ = chat.set_tripcode(password, token)

    if not viewership.is_allowed(token):
        if request.form.get('confirm'):
            return redirect(url_for('index'))
        viewers[token]['nickname'] = old_nickname
        viewers[token]['tripcode'] = old_tripcode
        return render_template('comment-confirm-iframe.html', token=token, nickname=old_nickname or viewership.default_nickname(token))

    viewership.preset_comment_iframe[token] = {'note': note, 'show_settings': True}
    return redirect(url_for('comment_iframe', token=token))

# TODO: undo hides; optionally show that a comment was hidden; optionally show bans in chat
@current_app.route('/mod/chat', methods=['POST'])
@current_app.auth.login_required
def mod_chat():
    message_ids = request.form.getlist('message_id[]')
    chat.mod_chat(message_ids, request.form.get('hide'), request.form.get('ban'), request.form.get('ban_purge'))
    return f'<meta http-equiv="refresh" content="0;url={url_for("chat_iframe")}"><div style="font-weight:bold;color:white;transform:scaleY(-1);">it is done</div>'

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
    viewership.made_request(token)
    if not viewership.is_allowed(token):
        return abort(403)

    embed_images = bool(request.args.get('embed', type=int))

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
    viewership.made_request()
    if not viewership.is_allowed(token):
        return abort(403)
    return render_template('users-iframe.html',
                           token=token,
                           people=viewership.get_people_list(),
                           default_nickname=viewership.default_nickname,
                           broadcaster=token == BROADCASTER_TOKEN,
                           debug=request.args.get('debug'),
                           broadcaster_colour=BROADCASTER_COLOUR,
                           background_colour=BACKGROUND_COLOUR,
                           len=len)

@current_app.route('/static/<fn>')
def _static(fn):
    token = get_token()
    if fn != 'eye.png' and not viewership.is_allowed(token):
        return abort(403)

    response = send_from_directory(DIR_STATIC, fn, add_etags=False)
    if fn == 'radial.apng':
        response.mimetype = 'image/png'
        response.headers['Cache-Control'] = 'no-store' # caching this in any way messes with the animation
    elif response.status_code == 200 and not fn.endswith('.png'):
        response.headers['Cache-Control'] = 'no-cache'
    return response

@current_app.route('/static/external/<fn>')
def third_party(fn):
    token = get_token()
    if not viewership.is_allowed(token):
        return abort(403)

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

@current_app.route('/debug')
@current_app.auth.login_required
def debug():
    import copy

    # necessary because we store colours as bytes and json can't bytes;
    class JSONEncoder(json.encoder.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, bytes):
                return f'#{obj.hex()}'
            return json.encoder.JSONEncoder.default(obj)


    with viewership.lock:
        # necessary because infinities are allowed by json.dumps but browsers don't like it
        json_safe_viewers = copy.deepcopy(viewership.viewers)
        for token in json_safe_viewers:
            for key in json_safe_viewers[token]:
                if json_safe_viewers[token][key] == float('-inf'):
                    json_safe_viewers[token][key] = None
                
        result = {
            'viewership': {
                 'segment_views': viewership.segment_views,
                 'video_was_corrupted': list(viewership.video_was_corrupted),
                 'viewers': json_safe_viewers,
                 'preset_comment_iframe': viewership.preset_comment_iframe
            },
            'chat': {
                'captchas': chat.captchas,
                'messages': list(chat.messages),
                'nonces': chat.nonces
            }
        }

    response = make_response(json.dumps(result, cls=JSONEncoder).replace('": -Infinity', '": null')) # this is such a horrible hack I apologise that you saw it
    response.mimetype = 'application/json'

    # so that you are logged in if the very first thing you do is go to /debug, then you go to /
    if get_token() != BROADCASTER_TOKEN:
        response.set_cookie('token', BROADCASTER_TOKEN)

    return response

@current_app.route('/reload')
@current_app.auth.login_required
def reload():
    '''
    Re-read config.toml
    '''
    with viewership.lock:
        with open(CONFIG_FILE) as fp:
            config = toml.load(fp)
        for key in config:
            CONFIG[key] = config[key]

    # this exists for the same reason as in /debug
    response = make_response(CONFIG)
    if get_token() != BROADCASTER_TOKEN:
        response.set_cookie('token', BROADCASTER_TOKEN)

    return response

@current_app.route('/teapot')
def teapot():
    return {'short': True, 'stout': True}, 418
