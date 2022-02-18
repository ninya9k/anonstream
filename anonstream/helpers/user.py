import hashlib
import base64
from collections import OrderedDict
from math import inf

from quart import current_app

from anonstream.utils.colour import generate_colour, colour_to_color

CONFIG = current_app.config

def generate_token_hash(token):
    parts = CONFIG['SECRET_KEY'] + b'token-hash\0' + token.encode()
    digest = hashlib.sha256(parts).digest()
    return base64.b32encode(digest)[:26].lower().decode()

def generate_user(timestamp, token, broadcaster):
    colour = generate_colour(
        seed='name\0' + token,
        bg=CONFIG['CHAT_BACKGROUND_COLOUR'],
        contrast=4.53,
    )
    return {
        'token': token,
        'token_hash': generate_token_hash(token),
        'websockets': set(),
        'broadcaster': broadcaster,
        'name': None,
        'color': colour_to_color(colour),
        'tripcode': None,
        'notices': OrderedDict(),
        'seen': {
            'first': timestamp,
            'last': timestamp,
        },
        'watching_last': -inf,
    }

def get_default_name(user):
    return (
        CONFIG['DEFAULT_HOST_NAME']
        if user['broadcaster'] else
        CONFIG['DEFAULT_ANON_NAME']
    )

def is_watching(timestamp, user):
    return user['watching_last'] >= timestamp - CONFIG['THRESHOLD_USER_IDLE']

def is_idle(timestamp, user):
    return is_present(timestamp, user) and not is_watching(timestamp, user)

def is_present(timestamp, user):
    return (
        user['seen']['last'] >= timestamp - CONFIG['THRESHOLD_USER_ABSENT']
        or len(user['websockets']) > 0
    )

def is_absent(timestamp, user):
    return not is_present(timestamp, user)

def is_visible(timestamp, messages, user):
    has_visible_messages = any(
        message['token'] == user['token'] for message in messages
    )
    return has_visible_messages or is_present(timestamp, user)
