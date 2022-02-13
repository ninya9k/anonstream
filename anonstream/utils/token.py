import secrets

def generate_token():
    return secrets.token_hex(16)
