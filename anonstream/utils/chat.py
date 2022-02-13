import base64
import hashlib
import secrets

def generate_nonce():
    return secrets.token_urlsafe(16)

def generate_message_id(secret, nonce):
    parts = secret + b'message-id\0' + nonce.encode()
    digest = hashlib.sha256(parts).digest()
    return base64.urlsafe_b64encode(digest)[:22].decode()
