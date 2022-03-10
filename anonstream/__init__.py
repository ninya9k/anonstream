# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import secrets
import toml
from collections import OrderedDict

from quart import Quart
from quart_compress import Compress
from werkzeug.security import generate_password_hash

from anonstream.utils.captcha import create_captcha_factory, create_captcha_signer
from anonstream.utils.colour import color_to_colour
from anonstream.utils.user import generate_token

compress = Compress()

def create_app(config_file):
    with open(config_file) as fp:
        config = toml.load(fp)

    auth_password = secrets.token_urlsafe(6)
    auth_pwhash = generate_password_hash(auth_password)
    print('Broadcaster username:', config['auth']['username'])
    print('Broadcaster password:', auth_password)

    app = Quart('anonstream')
    app.jinja_options.update({
        'trim_blocks': True,
        'lstrip_blocks': True,
    })
    app.config.update({
        'SECRET_KEY_STRING': config['secret_key'],
        'SECRET_KEY': config['secret_key'].encode(),
        'AUTH_USERNAME': config['auth']['username'],
        'AUTH_PWHASH': auth_pwhash,
        'AUTH_TOKEN': generate_token(),
        'SEGMENT_DIRECTORY': os.path.realpath(config['segments']['directory']),
        'SEGMENT_PLAYLIST': os.path.join(os.path.realpath(config['segments']['directory']), config['segments']['playlist']),
        'SEGMENT_PLAYLIST_CACHE_LIFETIME': config['segments']['playlist_cache_lifetime'],
        'SEGMENT_PLAYLIST_STALE_THRESHOLD': config['segments']['playlist_stale_threshold'],
        'SEGMENT_SEARCH_COOLDOWN': config['segments']['search_cooldown'],
        'SEGMENT_SEARCH_TIMEOUT': config['segments']['search_timeout'],
        'SEGMENT_STREAM_INITIAL_BUFFER': config['segments']['stream_initial_buffer'],
        'STREAM_TITLE': config['title']['file'],
        'STREAM_TITLE_CACHE_LIFETIME': config['title']['file_cache_lifetime'],
        'DEFAULT_HOST_NAME': config['names']['broadcaster'],
        'DEFAULT_ANON_NAME': config['names']['anonymous'],
        'MAX_STATES': config['memory']['states'],
        'MAX_CAPTCHAS': config['memory']['captchas'],
        'MAX_CHAT_MESSAGES': config['memory']['chat_messages'],
        'MAX_CHAT_SCROLLBACK': config['memory']['chat_scrollback'],
        'TASK_PERIOD_ROTATE_USERS': config['tasks']['rotate_users'],
        'TASK_PERIOD_ROTATE_CAPTCHAS': config['tasks']['rotate_captchas'],
        'TASK_PERIOD_BROADCAST_USERS_UPDATE': config['tasks']['broadcast_users_update'],
        'TASK_PERIOD_BROADCAST_STREAM_INFO_UPDATE': config['tasks']['broadcast_stream_info_update'],
        'THRESHOLD_USER_NOTWATCHING': config['thresholds']['user_notwatching'],
        'THRESHOLD_USER_TENTATIVE': config['thresholds']['user_tentative'],
        'THRESHOLD_USER_ABSENT': config['thresholds']['user_absent'],
        'THRESHOLD_NOJS_CHAT_TIMEOUT': config['thresholds']['nojs_chat_timeout'],
        'CHAT_COMMENT_MAX_LENGTH': config['chat']['max_name_length'],
        'CHAT_NAME_MAX_LENGTH': config['chat']['max_name_length'],
        'CHAT_NAME_MIN_CONTRAST': config['chat']['min_name_contrast'],
        'CHAT_BACKGROUND_COLOUR': color_to_colour(config['chat']['background_color']),
        'CHAT_LEGACY_TRIPCODE_ALGORITHM': config['chat']['legacy_tripcode_algorithm'],
        'FLOOD_DURATION': config['flood']['duration'],
        'FLOOD_THRESHOLD': config['flood']['threshold'],
        'CAPTCHA_LIFETIME': config['captcha']['lifetime'],
        'CAPTCHA_FONTS': config['captcha']['fonts'],
        'CAPTCHA_ALPHABET': config['captcha']['alphabet'],
        'CAPTCHA_LENGTH': config['captcha']['length'],
        'CAPTCHA_BACKGROUND_COLOUR': color_to_colour(config['captcha']['background_color']),
        'CAPTCHA_FOREGROUND_COLOUR': color_to_colour(config['captcha']['foreground_color']),
    })

    assert app.config['MAX_STATES'] >= 0
    assert app.config['MAX_CHAT_SCROLLBACK'] >= 0
    assert (
        app.config['MAX_CHAT_MESSAGES'] >= app.config['MAX_CHAT_SCROLLBACK']
    )
    assert (
        app.config['THRESHOLD_USER_ABSENT']
        >= app.config['THRESHOLD_USER_TENTATIVE']
        >= app.config['THRESHOLD_USER_NOTWATCHING']
    )

    app.messages_by_id = OrderedDict()
    app.messages = app.messages_by_id.values()

    app.users_by_token = {}
    app.users = app.users_by_token.values()

    app.captchas = OrderedDict()
    app.captcha_factory = create_captcha_factory(app.config['CAPTCHA_FONTS'])
    app.captcha_signer = create_captcha_signer(app.config['SECRET_KEY'])

    # State for tasks
    app.users_update_buffer = set()
    app.stream_title = None
    app.stream_uptime = None
    app.stream_viewership = None

    # Background tasks' asyncio.sleep tasks, cancelled on shutdown
    app.background_sleep = set()

    @app.after_serving
    async def shutdown():
        # make all background tasks finish
        for task in app.background_sleep:
            task.cancel()

    @app.before_serving
    async def startup():
        import anonstream.routes
        import anonstream.tasks

    # Compress some responses
    compress.init_app(app)
    app.config.update({
        "COMPRESS_MIN_SIZE": 2048,
        "COMPRESS_LEVEL": 9,
    })

    return app
