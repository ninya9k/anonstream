import secrets
import toml
from collections import OrderedDict

from quart import Quart
from werkzeug.security import generate_password_hash

from anonstream.utils.user import generate_token
from anonstream.utils.colour import color_to_colour
from anonstream.segments import DirectoryCache

def create_app():
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
        'CHECKUP_PERIOD_USER': config['intervals']['sunset_users'],
        'CHECKUP_PERIOD_CAPTCHA': config['intervals']['expire_captchas'],
        'THRESHOLD_USER_NOTWATCHING': config['thresholds']['user_notwatching'],
        'THRESHOLD_USER_TENTATIVE': config['thresholds']['user_tentative'],
        'THRESHOLD_USER_ABSENT': config['thresholds']['user_absent'],
        'THRESHOLD_NOJS_CHAT_TIMEOUT': config['thresholds']['nojs_chat_timeout'],
        'CHAT_COMMENT_MAX_LENGTH': config['chat']['max_name_length'],
        'CHAT_NAME_MAX_LENGTH': config['chat']['max_name_length'],
        'CHAT_NAME_MIN_CONTRAST': config['chat']['min_name_contrast'],
        'CHAT_BACKGROUND_COLOUR': color_to_colour(config['chat']['background_color']),
    })

    assert app.config['MAX_NOTICES'] >= 0
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
    app.users_by_token = {}
    app.messages = app.messages_by_id.values()
    app.users = app.users_by_token.values()
    app.segments_directory_cache = DirectoryCache(config['stream']['segments_dir'])

    @app.while_serving
    async def shutdown():
        app.shutting_down = False
        yield
        app.shutting_down = True

    @app.before_serving
    async def startup():
        import anonstream.routes
        import anonstream.tasks

    return app
