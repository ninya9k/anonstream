# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
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

def concatenate_for_notice(string, *tuples):
    if not tuples:
        return string
    markup = Markup(
        ''.join(
            f' <mark>{escape(x)}</mark>{escape(y)}'
            for x, y in tuples
        )
    )
    return string + markup

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
