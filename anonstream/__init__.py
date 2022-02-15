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
    app.config['SECRET_KEY'] = config['secret_key'].encode()
    app.config['AUTH_USERNAME'] = config['auth']['username']
    app.config['AUTH_PWHASH'] = auth_pwhash
    app.config['AUTH_TOKEN'] = generate_token()
    app.config['DEFAULT_HOST_NAME'] = config['names']['broadcaster']
    app.config['DEFAULT_ANON_NAME'] = config['names']['anonymous']
    app.config['LIMIT_NOTICES'] = config['limits']['notices']
    app.chat = OrderedDict()
    app.users = {}
    app.websockets = set()
    app.segments_directory_cache = DirectoryCache(config['stream']['segments_dir'])

    async with app.app_context():
        import anonstream.routes

    return app
