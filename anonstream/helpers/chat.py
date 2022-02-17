import hashlib

from quart import current_app

CONFIG = current_app.config

def generate_nonce_hash(nonce):
    parts = CONFIG['SECRET_KEY'] + b'nonce-hash\0' + nonce.encode()
    return hashlib.sha256(parts).digest()
