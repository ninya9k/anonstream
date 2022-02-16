import base64
import hashlib
import secrets
from collections import OrderedDict
from math import inf

def generate_token():
    return secrets.token_hex(16)

def generate_token_hash(secret, token):
    parts = secret + b'token-hash\0' + token.encode()
    digest = hashlib.sha256(parts).digest()
    return base64.b32encode(digest)[:26].lower().decode()

def generate_user(secret, token, broadcaster, timestamp):
    return {
        'token': token,
        'token_hash': generate_token_hash(secret, token),
        'broadcaster': broadcaster,
        'name': None,
        'color': '#c7007f',
        'tripcode': None,
        'notices': OrderedDict(),
        'seen': {
            'first': timestamp,
            'last': timestamp,
        },
        'watching_last': -inf,
    }

def user_for_websocket(user, include_token_hash=True):
    keys = ['broadcaster', 'name', 'color', 'tripcode']
    if include_token_hash:
        keys.append('token_hash')
    return {key: user[key] for key in keys}
