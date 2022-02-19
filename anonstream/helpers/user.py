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
