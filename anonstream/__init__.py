import secrets
import toml
from collections import OrderedDict

from quart import Quart
from werkzeug.security import generate_password_hash

from anonstream.utils.user import generate_token
from anonstream.utils.colour import color_to_colour
from anonstream.segments import DirectoryCache

async def create_app():
    with open('config.toml') as fp:
        config = toml.load(fp)

    auth_password = secrets.token_urlsafe(6)
    auth_pwhash = generate_password_hash(auth_password)
    print('Broadcaster username:', config['auth']['username'])
    print('Broadcaster password:', auth_password)

    app = Quart('anonstream')
    app.config.update({
        'SECRET_KEY': config['secret_key'].encode(),
        'AUTH_USERNAME': config['auth']['username'],
        'AUTH_PWHASH': auth_pwhash,
        'AUTH_TOKEN': generate_token(),
        'DEFAULT_HOST_NAME': config['names']['broadcaster'],
        'DEFAULT_ANON_NAME': config['names']['anonymous'],
        'MAX_NOTICES': config['memory']['notices'],
        'MAX_CHAT_MESSAGES': config['memory']['chat_messages'],
        'MAX_CHAT_SCROLLBACK': config['memory']['chat_scrollback'],
        'CHECKUP_PERIOD_USER': config['ratelimits']['user_absence'],
        'CHECKUP_PERIOD_CAPTCHA': config['ratelimits']['captcha_expiry'],
        'THRESHOLD_IDLE': config['thresholds']['idle'],
        'THRESHOLD_ABSENT': config['thresholds']['absent'],
        'CHAT_COMMENT_MAX_LENGTH': config['chat']['max_name_length'],
        'CHAT_NAME_MAX_LENGTH': config['chat']['max_name_length'],
        'CHAT_NAME_MIN_CONTRAST': config['chat']['min_name_contrast'],
        'CHAT_BACKGROUND_COLOUR': color_to_colour(config['chat']['background_color']),
    })

    assert app.config['MAX_CHAT_MESSAGES'] >= app.config['MAX_CHAT_SCROLLBACK']
    assert app.config['THRESHOLD_ABSENT'] >= app.config['THRESHOLD_IDLE']

    app.messages_by_id = OrderedDict()
    app.users_by_token = {}
    app.messages = app.messages_by_id.values()
    app.users = app.users_by_token.values()
    app.segments_directory_cache = DirectoryCache(config['stream']['segments_dir'])

    async with app.app_context():
        import anonstream.routes

    return app
