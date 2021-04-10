from flask import Flask, render_template, send_from_directory, request, abort, Response, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from flask_compress import Compress
import werkzeug
import werkzeug.security
import os
import time
import threading
import hashlib
import secrets
import unicodedata
from captcha.image import ImageCaptcha
import string
import base64
import io
import math
from datetime import datetime

from pprint import pprint

from concatenate import ConcatenatedSegments, _is_segment, _segment_number
from colour import gen_colour, _contrast, _distance_sq

# Override HTTP headers globally https://stackoverflow.com/a/46858238
class LocalFlask(Flask):
    def process_response(self, response):
        # Every response will be processed here first
        super().process_response(response)
        response.headers['Server'] = 'Werkzeug'
        return response


app = LocalFlask(__name__)
auth = HTTPBasicAuth()
compress = Compress()
compress.init_app(app)

ROOT = os.path.split(app.instance_path)[0]
SEGMENTS_DIR = os.path.join(ROOT, 'stream')
SEGMENTS_M3U8 = os.path.join(SEGMENTS_DIR, 'stream.m3u8')
STREAM_TITLE = os.path.join(ROOT, 'title.txt')

HLS_TIME     = 10   # seconds per segment
VIEWS_PERIOD = 30   # count views from the last 30 seconds
CHAT_TIMEOUT = 5    # seconds between chat messages
FLOOD_PERIOD = 20   # seconds
FLOOD_THRESHOLD = 3 # messages in FLOOD_PERIOD seconds

viewers = {}
lock = threading.Lock()

chat = []
captchas = {}

CAPTCHA_CHARSET = '346qwertypagkxvbm'
CAPTCHA_LENGTH = 3
CAPTCHA_FONTS = ['/usr/share/fonts/truetype/freefont/FreeMono.ttf',
                 '/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf',
                 '/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf',
                 '/usr/share/fonts/truetype/tlwg/TlwgMono.ttf']
CAPTCHA = ImageCaptcha(width=72, height=30, fonts=CAPTCHA_FONTS, font_sizes=(24, 27, 30))

segment_views = {}

broadcaster_pw = secrets.token_urlsafe(6)
broadcaster_token = secrets.token_hex(8)

BACKGROUND_COLOUR = (0x23, 0x23, 0x23)

# notes: messages that can appear in the comment box
N_NONE            =  0
N_TOKEN_EMPTY     =  1
N_MESSAGE_EMPTY   =  2
N_MESSAGE_LONG    =  3
N_BANNED          =  4
N_TOOFAST         =  5
N_FLOOD           =  6
N_CAPTCHA_MISSING =  7
N_CAPTCHA_WRONG   =  8
N_CAPTCHA_RANDOM  =  9
N_APPEAR_OK       = 10
N_APPEAR_FAIL     = 11

NOTES = {N_NONE:            '',
         N_TOKEN_EMPTY:     'illegal token',
         N_MESSAGE_EMPTY:   'no message',
         N_MESSAGE_LONG:    'message too long',
         N_BANNED:          'you cannot chat',
         N_TOOFAST:         'resend your message',
         N_FLOOD:           'solve this captcha',
         N_CAPTCHA_MISSING: 'please captcha',
         N_CAPTCHA_WRONG:   'you got the captcha wrong',
         N_CAPTCHA_RANDOM:  'a wild captcha appears',
         N_APPEAR_OK:       'appearance got changed',
         N_APPEAR_FAIL:     'name/pw too long; no change'}

#When a viewer leaves a comment, they make a POST request to /comment; either
#you can redirect back to /comment-box or you can respond there without
#redirecting. In the second case viewers will get a confirmation dialogue when
#they refresh the page; in the first case, you need to somehow give them the
#note exactly once. That's what this dict is for.
preset_comment_iframe = {}

@auth.verify_password
def verify_password(username, password):
    if username == 'broadcaster' and password == broadcaster_pw:
        return username

print('Broadcaster password:', broadcaster_pw)

def set_default_viewer(token):
    if token in viewers:
        return
    viewers[token] = {'token': token, 'comment': float('-inf'), 'heartbeat': int(time.time()), 'verified': False, 'recent_comments': [], 'nickname': 'Anonymous', 'colour': gen_viewer_colour(token.encode()), 'banned': False, 'tripcode': default_tripcode(), 'broadcaster': False}
    if token == broadcaster_token:
        viewers[token]['broadcaster'] = True
        viewers[token]['colour'] = b'\xff\x82\x80'
        viewers[token]['nickname'] = 'Broadcaster'
        viewers[token]['verified'] = True

def default_nickname(token):
    if token == broadcaster_token:
        return 'Broadcaster'
    return 'Anonymous'

def default_tripcode():
    return {'string': None, 'background_colour': None, 'foreground_colour': None}

def new_token(short=False):
    return secrets.token_hex(4 if short else 8)

@app.route('/')
def index(token=None):
    token = token or request.args.get('token') or request.cookies.get('token') or new_token()
    set_default_viewer(token)
    response = Response(render_template('index.html', token=token))
    response.set_cookie('token', token)
    return response

@app.route('/broadcaster')
@auth.login_required
def broadcaster():
    return index(token=broadcaster_token)

@app.route('/stream.m3u8')
def playlist():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    response = send_from_directory(SEGMENTS_DIR, 'stream.m3u8', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    response.set_cookie('token', token)
    return response

@app.route('/init.mp4')
def segment_init():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    response = send_from_directory(SEGMENTS_DIR, f'init.mp4', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/stream<int:n>.m4s')
def segment_arbitrary(n):
    token = request.args.get('token') or request.cookies.get('token')
    _view_segment(n, token)
    response = send_from_directory(SEGMENTS_DIR, f'stream{n}.m4s', add_etags=False)
    response.headers['Cache-Control'] = 'no-cache'
    if token == None:
        token = new_token()
        response.set_cookie('token', token)
    return response

def _view_segment(n, token=None):
    # n is None if segment_hook is called in ConcatenatedSegments and the current segment is init.mp4
    if n == None:
        return

    if not os.path.isfile(os.path.join(SEGMENTS_DIR, f'stream{n}.m4s')):
        return

    with lock:
        now = int(time.time())
        segment_views.setdefault(n, []).append({'time': now, 'token': token})
        print(f'seg{n}: {token}')

@app.route('/stream.mp4')
def stream():
    token = request.cookies.get('token')
    # TODO: check what happens when /stream.mp4 gets very delayed
    concatenated_segments = ConcatenatedSegments(SEGMENTS_DIR, segment_hook=lambda n: _view_segment(n, token))
    file_wrapper = werkzeug.wrap_file(request.environ, concatenated_segments)
    return Response(file_wrapper, mimetype='video/mp4')

# TODO: make `chat` a object with O(1) time appending to the front
@app.route('/chat')
def chat_iframe():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    messages = (message for message in reversed(chat) if not message['hidden'])
    messages = zip(messages, range(64))
    messages = (message for message, _ in messages)
    return render_template('chat-iframe.html', token=token, messages=messages, broadcaster=token == broadcaster_token)

def count_site_tokens():
    '''
    Return the number of viewers who have sent a heartbeat or commented in the last 30 seconds
    '''
    n = 0
    now = int(time.time())
    for token in set(viewers):
        if max(viewers[token]['heartbeat'], viewers[token]['comment']) >= now - VIEWS_PERIOD:
            n += 1
    return n

def count_segment_views(exclude_token_views=True):
    '''
    Estimate the number of viewers using only the number of views segments have had in the last 30 seconds
    If `exclude_token_views` is True then ignore views with associated tokens
    '''
    if not segment_views: # what?
        return 0

    # create the list of streaks; a streak is a sequence of consequtive segments with non-zero views
    streaks = [] # TODO: check this works
    streak = []
    for i in range(min(segment_views), max(segment_views)):
        _views = segment_views.get(i, [])
        if exclude_token_views:
            _views = filter(lambda _view: _view['token'] == None, _views)
            _views = list(_views)
        if len(_views) == 0:
            streaks.append(streak)
            streak = []
        elif streak != []:
            streak.append(len(_views))

    total_viewers = 0
    for streak in streaks:
        n = 0
        _previous_n_views = 0
        for _n_views in streak:
            # any increase in views from one segment to the next means there must be new viewer
            n += max(_n_views - _previous_n_views, 0) 
        total_viewers += n

    print(f'{streaks=}')

    # this assumes every viewer views exactly VIEWS_PERIOD / HLS_TIME segments
    average_viewers = sum(sum(streak) for streak in streaks) * HLS_TIME / VIEWS_PERIOD

    print(f'count_segment_views: {total_viewers=}, {average_viewers=}')
    return max(total_viewers, math.ceil(average_viewers))

def count_segment_tokens():
    # remove old views
    now = int(time.time())
    for i in segment_views:
        for view in segment_views[i].copy():
            view_timestamp, view_token = view
            if view_timestamp < now - VIEWS_PERIOD:
                segment_views[i].remove(view)

    tokens = set()
    for i in segment_views:
        for view_timestamp, view_token in segment_views[i]:
            tokens.add(view_token)
    return len(tokens)

def n_viewers():
    with lock:
        a, b = count_segment_tokens(), count_segment_views(exclude_token_views=True)
        print(f'count_segment_tokens={a}; count_segment_views={b}')
        return a + b

def current_segment():
    files = os.listdir(SEGMENTS_DIR)

    try:
        m3u8 = open(SEGMENTS_M3U8).read()
    except FileNotFoundError:
        return None

    files = filter(lambda fn: fn in m3u8, files)

    try:
        last_segment = max(filter(_is_segment, files), key=_segment_number)
        return _segment_number(last_segment)
    except ValueError:
        return None

def stream_is_online():
    return os.path.exists(SEGMENTS_M3U8) and True # TODO: check if ffmpeg is running

def stream_title():
    try:
        return open(STREAM_TITLE).read().strip()
    except FileNotFoundError:
        return 'onion livestream'

@app.route('/heartbeat')
def heartbeat():
    now = int(time.time())
    token = request.args.get('token') or request.cookies.get('token')
    if token in viewers:
        viewers[token]['heartbeat'] = int(time.time())
    return {'viewers': n_viewers(),
            'online': stream_is_online(),
            'current_segment': current_segment(),
            'title': stream_title()}

def _image_to_base64(im):
    buffer = io.BytesIO()
    im.save(buffer, format='jpeg', quality=70)
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).rstrip(b'=')
    return (b'data:image/jpeg;base64,' + b64).decode()

def gen_captcha():
    answer = ''.join(secrets.choice(CAPTCHA_CHARSET) for _ in range(CAPTCHA_LENGTH))
    im = CAPTCHA.create_captcha_image(answer, (0xff, 0xff, 0xff), BACKGROUND_COLOUR)
    return _image_to_base64(im), answer

@app.route('/comment-box')
def comment_iframe():
    token = request.args.get('token') or request.cookies.get('token') or new_token()

    try:
        preset = preset_comment_iframe.pop(token)
    except KeyError:
        note = N_NONE
        message = ''
    else:
        note = preset.get('note', N_NONE)
        message = preset.get('message', '')

    if note not in NOTES:
        note = N_NONE

    captcha = None
    set_default_viewer(token)

    if not viewers[token]['verified']:
        c_src, c_answer = gen_captcha()
        c_token = new_token()
        captchas[c_token] = c_answer
        captcha = {'src': c_src, 'token': c_token}

    default = default_nickname(token)
    nickname = viewers[token]['nickname']
    nickname = nickname if nickname != default else ''

    response = Response(render_template('comment-iframe.html',
                                         token=token,
                                         captcha=captcha,
                                         note=NOTES[note],
                                         message=message,
                                         default=default,
                                         nickname=nickname,
                                         viewer=viewers[token],
                                         show_settings=note == N_APPEAR_OK or note == N_APPEAR_FAIL))
    response.set_cookie('token', token)
    return response

# TODO: make this better
def gen_viewer_colour(seed, background=b'\x22\x22\x22'):
    for _ in range(16384): # in case we run out of colours
        colour = gen_colour(seed, background)
        if all(1 < _contrast(colour, viewers[token]['colour']) for token in viewers):
            return colour
    return colour

def behead_chat():
    while len(chat) > 1024:
        chat.pop(0)

@app.route('/comment', methods=['POST'])
def comment():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    message = request.form.get('message', '').replace('\r', '').replace('\n', ' ').strip()
    c_response = request.form.get('captcha')
    c_token = request.form.get('captcha-token')

    failure_reason = N_NONE
    with lock:
        now = int(time.time())
        if not token:
            failure_reason = N_TOKEN_EMPTY
        elif not message:
            failure_reason = N_MESSAGE_EMPTY
        elif len(message) >= 256:
            failure_reason = N_MESSAGE_LONG
        else:
            set_default_viewer(token)
            # remove record of old comments
            for t in viewers[token]['recent_comments'].copy():
                if t < now - FLOOD_PERIOD:
                    viewers[token]['recent_comments'].remove(t)

            pprint(viewers)
            if viewers[token]['banned']:
                failure_reason = N_BANNED
            elif now < viewers[token]['comment'] + CHAT_TIMEOUT:
                failure_reason = N_TOOFAST
            elif len(viewers[token]['recent_comments']) + 1 >= FLOOD_THRESHOLD:
                failure_reason = N_FLOOD
                viewers[token]['verified'] = False
            elif not viewers[token]['verified'] and c_token not in captchas:
                failure_reason = N_CAPTCHA_MISSING
            elif not viewers[token]['verified'] and captchas[c_token] != c_response:
                failure_reason = N_CAPTCHA_WRONG
            elif secrets.randbelow(50) == 0:
                failure_reason = N_CAPTCHA_RANDOM
                viewers[token]['verified'] = False
            else:
                dt = datetime.utcfromtimestamp(now)
                chat.append({'text': message,
                              'viewer': viewers[token],
                              'id': f'{token}-{new_token(short=True)}',
                              'hidden': False,
                              'time': dt.strftime('%H:%M'),
                              'date': dt.strftime('%F %T')})
                viewers[token]['comment'] = now
                viewers[token]['recent_comments'].append(now)
                viewers[token]['verified'] = True
                behead_chat()

    set_default_viewer(broadcaster_token)
    viewers[broadcaster_token]['verified'] = True

    # TODO: consider eliminating the POST->GET pattern for speed reasons
    preset_comment_iframe[token] = {'note': failure_reason, 'message': message if failure_reason else ''}
    return redirect(url_for('comment_iframe', token=token))

# TODO: make it so your message that you haven't sent yet stays there when you change your appearance
@app.route('/settings', methods=['POST'])
def settings():
    token = request.args.get('token') or request.cookies.get('token') or new_token()
    set_default_viewer(token)

    nickname = request.form.get('nickname', '').strip()
    nickname = ''.join(char if unicodedata.category(char) != 'Cc' else ' ' for char in nickname).strip()

    if len(nickname) > 24:
        preset_comment_iframe[token] = {'note': N_APPEAR_FAIL}
        return redirect(url_for('comment_iframe', token=token))

    if request.form.get('remove-tripcode'):
        viewers[token]['tripcode'] = default_tripcode()
    elif request.form.get('set-tripcode'):
        password = request.form.get('password', '')
        if len(password) > 256:
            preset_comment_iframe[token] = {'note': N_APPEAR_FAIL}
            return redirect(url_for('comment_iframe', token=token))
        pwhash = werkzeug.security._hash_internal('pbkdf2:sha256', b'\0', password)[0]
        tripcode = bytes.fromhex(pwhash)[:6]
        viewers[token]['tripcode']['string'] = base64.b64encode(tripcode).decode()
        viewers[token]['tripcode']['background_colour'] = gen_colour(tripcode, BACKGROUND_COLOUR)
        viewers[token]['tripcode']['foreground_colour'] = max((b'\0\0\0', b'\x3f\x3f\x3f', b'\x7f\x7f\x7f', b'\xbf\xbf\xbf', b'\xff\xff\xff'),
                                                              key=lambda c: _distance_sq(c, viewers[token]['tripcode']['background_colour']))

    viewers[token]['nickname'] = nickname or default_nickname(token)

    preset_comment_iframe[token] = {'note': N_APPEAR_OK}
    return redirect(url_for('comment_iframe', token=token))

@app.route('/mod', methods=['POST'])
@auth.login_required
def mod():
    message_ids = request.form.getlist('message_id[]')
    _ban_and_purge  = request.form.get('ban_purge')
    _purge  = _ban_and_purge
    _hide = request.form.get('hide')
    _ban    = _ban_and_purge or request.form.get('ban')

    if _ban:
        banned = {message_id.split('-')[0] for message_id in message_ids}
        for token in banned:
            viewers[token]['banned'] = True
    for message in chat:
        if _hide and message['id'] in message_ids:
            message['hidden'] = True
        if _purge and message['viewer']['token'] in banned:
            message['hidden'] = True

    set_default_viewer(broadcaster_token)
    viewers[broadcaster_token]['banned'] = False

    return f'<meta http-equiv="refresh" content="0;url={url_for("chat_iframe")}"><div style="font-weight:bold;color:white;transform: scaleY(-1);">it is done</div>'

@app.route('/stream-info')
def stream_info():
    return render_template('stream-info-iframe.html',
                           title=stream_title(),
                           viewer_count=n_viewers(),
                           online=stream_is_online())
