import base64
import hashlib
import secrets

class NonceReuse(Exception):
    pass

def generate_nonce():
    return secrets.token_urlsafe(16)

def generate_nonce_hash(secret, nonce):
    parts = secret + b'nonce-hash\0' + nonce.encode()
    return hashlib.sha256(parts).digest()

def message_for_websocket(users, message):
    message_keys = ('id', 'date', 'time_minutes', 'time_seconds', 'markup')
    user_keys = ('token_hash',)

    user = users[message['token']]
    return {
        **{key: message[key] for key in message_keys},
        **{key: user[key] for key in user_keys},
    }
