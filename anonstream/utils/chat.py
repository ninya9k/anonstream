import base64
import hashlib
import secrets

class NonceReuse(Exception):
    pass

def generate_nonce():
    return secrets.token_urlsafe(16)

def generate_message_id(secret, nonce):
    parts = secret + b'message-id\0' + nonce.encode()
    digest = hashlib.sha256(parts).digest()
    return base64.urlsafe_b64encode(digest)[:22].decode()

def create_message(message_ids, secret, nonce, comment):
    message_id = generate_message_id(secret, nonce)
    if message_id in message_ids:
        raise NonceReuse
    return message_id, nonce, comment
