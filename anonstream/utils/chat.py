import base64
import hashlib
import secrets

class NonceReuse(Exception):
    pass

def generate_nonce():
    return secrets.token_urlsafe(16)

def message_for_websocket(user, message):
    message_keys = ('seq', 'date', 'time_minutes', 'time_seconds', 'markup')
    user_keys = ('token_hash',)
    return {
        **{key: message[key] for key in message_keys},
        **{key: user[key] for key in user_keys},
    }
