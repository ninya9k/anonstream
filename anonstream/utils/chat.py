# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import hashlib
import math
import secrets

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
