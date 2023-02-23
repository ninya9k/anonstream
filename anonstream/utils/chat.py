# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import hashlib
import math
import re
import secrets
from datetime import datetime
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

def should_show_initial_date(timestamp, messages):
    try:
        first_message = next(iter(messages))
    except StopIteration:
        return False
    if any(message['date'] != first_message['date'] for message in messages):
        return True
    else:
        latest_date = max(map(lambda message: message['date'], messages))
        date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
        return date != latest_date
