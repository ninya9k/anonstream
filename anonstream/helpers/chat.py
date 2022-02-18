import hashlib

from quart import current_app

CONFIG = current_app.config

def generate_nonce_hash(nonce):
    parts = CONFIG['SECRET_KEY'] + b'nonce-hash\0' + nonce.encode()
    return hashlib.sha256(parts).digest()

def get_scrollback(messages):
    n = CONFIG['MAX_CHAT_SCROLLBACK']
    if len(messages) < n:
        return messages
    return list(messages)[-n:]
