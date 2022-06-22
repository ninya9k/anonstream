# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import base64
from collections import deque, OrderedDict
from math import inf

from quart import current_app

from anonstream.utils.colour import generate_colour, colour_to_color
from anonstream.utils.user import Presence

CONFIG = current_app.config

def generate_token_hash_and_tag(token):
    parts = CONFIG['SECRET_KEY'] + b'token-hash\0' + token.encode()
    digest = hashlib.sha256(parts).digest()

    token_hash = base64.b32encode(digest)[:26].lower().decode()
    tag = f'#{digest.hex()[:3]}'

    return token_hash, tag

def generate_user(timestamp, token, broadcaster, presence):
    colour = generate_colour(
        seed='name\0' + token,
        bg=CONFIG['CHAT_BACKGROUND_COLOUR'],
        min_contrast=4.53,
    )
    token_hash, tag = generate_token_hash_and_tag(token)
    return {
        'token': token,
        'token_hash': token_hash,
        'tag': tag,
        'broadcaster': broadcaster,
        'verified': broadcaster,
        'websockets': {},
        'name': None,
        'color': colour_to_color(colour),
        'tripcode': None,
        'state': OrderedDict(),
        'last': {
            'seen': timestamp,
            'watching': -inf,
            'eyes': -inf,
            'reading': -inf,
        },
        'presence': presence,
        'linespan': deque(),
        'eyes': {
            'total': 0,
            'current': {},
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
    if last_watching_ago < CONFIG['PRESENCE_NOTWATCHING']:
        return Presence.WATCHING

    last_seen_ago = timestamp - user['last']['seen']
    if last_seen_ago < CONFIG['PRESENCE_TENTATIVE']:
        return Presence.NOTWATCHING
    if user['websockets']:
        return Presence.NOTWATCHING

    if last_seen_ago < CONFIG['PRESENCE_ABSENT']:
        return Presence.TENTATIVE

    return Presence.ABSENT
