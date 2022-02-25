import hashlib
import base64
from collections import OrderedDict
from enum import Enum
from math import inf

from quart import current_app

from anonstream.utils.colour import generate_colour, colour_to_color

CONFIG = current_app.config

Presence = Enum(
    'Presence',
    names=(
        'WATCHING',
        'NOTWATCHING',
        'TENTATIVE',
        'ABSENT',
    )
)

def generate_token_hash_and_tag(token):
    parts = CONFIG['SECRET_KEY'] + b'token-hash\0' + token.encode()
    digest = hashlib.sha256(parts).digest()

    token_hash = base64.b32encode(digest)[:26].lower().decode()
    tag = f'#{digest.hex()[:3]}'

    return token_hash, tag

def generate_user(timestamp, token, broadcaster):
    colour = generate_colour(
        seed='name\0' + token,
        bg=CONFIG['CHAT_BACKGROUND_COLOUR'],
        contrast=4.53,
    )
    token_hash, tag = generate_token_hash_and_tag(token)
    return {
        'token': token,
        'token_hash': token_hash,
        'tag': tag,
        'broadcaster': broadcaster,
        'verified': broadcaster,
        'websockets': set(),
        'name': None,
        'color': colour_to_color(colour),
        'tripcode': None,
        'state': OrderedDict(),
        'last': {
            'seen': timestamp,
            'watching': -inf,
        },
    }

def get_default_name(user):
    return (
        CONFIG['DEFAULT_HOST_NAME']
        if user['broadcaster'] else
        CONFIG['DEFAULT_ANON_NAME']
    )

def get_presence(timestamp, user):
    last_watching_ago = timestamp - user['last']['watching']
    if last_watching_ago < CONFIG['THRESHOLD_USER_NOTWATCHING']:
        return Presence.WATCHING

    last_seen_ago = timestamp - user['last']['seen']
    if last_seen_ago < CONFIG['THRESHOLD_USER_TENTATIVE']:
        return Presence.NOTWATCHING
    if user['websockets']:
        return Presence.NOTWATCHING

    if last_seen_ago < CONFIG['THRESHOLD_USER_ABSENT']:
        return Presence.TENTATIVE

    return Presence.ABSENT

def is_watching(timestamp, user):
    return get_presence(timestamp, user) == Presence.WATCHING

def is_listed(timestamp, user):
    return (
        get_presence(timestamp, user)
        in {Presence.WATCHING, Presence.NOTWATCHING}
    )

def is_visible(timestamp, messages, user):
    def user_left_messages():
        return any(
            message['token'] == user['token']
            for message in messages
        )
    return is_listed(timestamp, user) or user_left_messages()
