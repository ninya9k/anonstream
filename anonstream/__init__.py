import secrets
import toml
from collections import OrderedDict

from quart import Quart
from werkzeug.security import generate_password_hash

from anonstream.utils.token import generate_token
from anonstream.segments import DirectoryCache

async def create_app():
    with open('config.toml') as fp:
        config = toml.load(fp)

    auth_password = secrets.token_urlsafe(6)
    auth_pwhash = generate_password_hash(auth_password)
    print('Broadcaster username:', config['auth_username'])
    print('Broadcaster password:', auth_password)

    app = Quart('anonstream')
    app.config['SECRET_KEY'] = config['secret_key'].encode()
    app.config['AUTH_USERNAME'] = config['auth_username']
    app.config['AUTH_PWHASH'] = auth_pwhash
    app.config['AUTH_TOKEN'] = generate_token()
    app.chat = OrderedDict()
    app.websockets = {}
    app.segments_directory_cache = DirectoryCache(config['segments_dir'])

    async with app.app_context():
        import anonstream.routes

    return app
