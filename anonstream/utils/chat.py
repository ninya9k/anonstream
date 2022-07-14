# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import hashlib
import math
import re
import secrets
from functools import lru_cache

from quart import escape

class NonceReuse(Exception):
    pass

def generate_nonce():
    return secrets.token_urlsafe(16)

def get_message_for_websocket(user, message):
    message_keys = ('seq', 'date', 'time_minutes', 'time_seconds', 'markup')
    user_keys = ('token_hash',)
    return {
        **{key: message[key] for key in message_keys},
        **{key: user[key] for key in user_keys},
    }

def get_approx_linespan(text):
    def height(line):
        return math.ceil(len(line) / 48)
    linespan = sum(map(height, text.splitlines()))
    linespan = linespan if linespan > 0 else 1
    return linespan

def schema_to_emotes(schema):
    emotes = []
    for name, coords in schema.items():
        assert not re.search(r'\s', name), \
            'whitespace is not allowed in emote names'
        name_markup = escape(name)
        regex = re.compile(
            r'(?:^|(?<=\s|\W))%s(?:$|(?=\s|\W))' % re.escape(name_markup)
        )
        position, size = tuple(coords['position']), tuple(coords['size'])
        emotes.append((name, regex, position, size))
    return emotes

def escape_css_string(string):
    '''
    https://drafts.csswg.org/cssom/#common-serializing-idioms
    '''
    result = []
    for char in string:
        if char == '\0':
            result.append('\ufffd')
        elif char < '\u0020' or char == '\u007f':
            result.append(f'\\{ord(char):x}')
        elif char == '"' or char == '\\':
            result.append(f'\\{char}')
        else:
            result.append(char)
    return ''.join(result)

@lru_cache(maxsize=1)
def get_emotehash(emotes):
    rules = []
    for name, _regex, (x, y), (width, height) in sorted(emotes):
        rule = (
            f'[data-emote="{escape_css_string(name)}"] '
            f'{{ background-position: {-x}px {-y}px; '
            f'width: {width}px; height: {height}px; }}'
        )
        rules.append(rule.encode())
    plaintext = b','.join(rules)
    digest = hashlib.sha256(plaintext).digest()
    return digest[:6].hex()
