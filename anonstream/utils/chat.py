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

def precompute_emote_regex(schema):
    for emote in schema:
        assert emote['name'], 'emote names cannot be empty'
        assert not re.search(r'\s', emote['name']), \
            f'whitespace is not allowed in emote names: {emote["name"]!r}'
        for length in (emote['width'], emote['height']):
            assert length is None or isinstance(length, int) and length >= 0, \
                f'emote dimensions must be null or non-negative integers: {emote["name"]!r}'
        # If the emote name begins with a word character [a-zA-Z0-9_],
        # match only if preceded by a non-word character or the empty
        # string.  Similarly for the end of the emote name.
        # Examples:
        #  * ":joy:" matches "abc :joy:~xyz"   and   "abc:joy:xyz"
        #  * "JoySi" matches "abc JoySi~xyz" but NOT "abcJoySiabc"
        onset = r'(?:^|(?<=\W))' if re.fullmatch(r'\w', emote['name'][0]) else r''
        finish = r'(?:$|(?=\W))' if re.fullmatch(r'\w', emote['name'][-1]) else r''
        emote['regex'] = re.compile(''.join(
            (onset, re.escape(escape(emote['name'])), finish)
        ))
