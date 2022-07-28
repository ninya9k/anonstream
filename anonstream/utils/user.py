# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import hashlib
import secrets
from collections import OrderedDict
from enum import Enum
from math import inf

from quart import escape, Markup

USER_WEBSOCKET_ATTRS = {'broadcaster', 'name', 'color', 'tripcode', 'tag'}

Presence = Enum(
    'Presence',
    names=(
        'WATCHING',
        'NOTWATCHING',
        'TENTATIVE',
        'ABSENT',
    )
)

def generate_token():
    return secrets.token_hex(16)

def trilean(presence):
    match presence:
        case Presence.WATCHING:
            return True
        case Presence.NOTWATCHING:
            return False
        case _:
            return None

def get_user_for_websocket(user):
    return {
        **{key: user[key] for key in USER_WEBSOCKET_ATTRS},
        'watching': trilean(user['presence']),
    }

def identifying_string(user, ansi=True):
    tag = user['tag']
    token_hash = f'{user["token_hash"][:4]}..'
    token = user['token']
    if ansi:
        tag = f'\033[36m{tag}\033[0m'
        token_hash = f'\033[32m{token_hash}\033[0m'
        token = f'\033[35m{token}\033[0m'
    return '/'.join((tag, token_hash, token))

def generate_blank_allowedness():
    return {
        'blacklist': {
            ('token',): set(),
            ('token_hash',): set(),
        },
        'whitelist': {
            ('token',): set(),
            ('token_hash',): set(),
            ('tripcode', 'digest'): set(),
        },
        'default': True,
    }
