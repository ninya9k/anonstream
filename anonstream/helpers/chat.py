# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib

from quart import current_app

CONFIG = current_app.config

def generate_nonce_hash(nonce):
    parts = CONFIG['SECRET_KEY'] + b'nonce-hash\0' + nonce.encode()
    return hashlib.sha256(parts).hexdigest()

def get_scrollback(messages):
    n = CONFIG['MAX_CHAT_SCROLLBACK']
    if len(messages) < n:
        return messages
    return list(messages)[-n:]
