import secrets
import toml
from collections import OrderedDict

from quart import Quart
from werkzeug.security import generate_password_hash

from anonstream.utils.users import generate_token
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
        'MAX_NOTICES': config['limits']['notices'],
        'MAX_CHAT_STORAGE': config['limits']['chat_storage'],
        'MAX_CHAT_SCROLLBACK': config['limits']['chat_scrollback'],
        'USER_CHECKUP_PERIOD': config['ratelimits']['user_absence'],
        'CAPTCHA_CHECKUP_PERIOD': config['ratelimits']['captcha_expiry'],
        'THRESHOLD_IDLE': config['thresholds']['idle'],
        'THRESHOLD_ABSENT': config['thresholds']['absent'],
    })

    assert app.config['THRESHOLD_ABSENT'] >= app.config['THRESHOLD_IDLE']

    app.chat = {'messages': OrderedDict(), 'nonce_hashes': set()}
    app.users = {}
    app.websockets = set()
    app.segments_directory_cache = DirectoryCache(config['stream']['segments_dir'])

    async with app.app_context():
        import anonstream.routes

    return app
