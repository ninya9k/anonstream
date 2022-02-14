import secrets

def generate_token():
    return secrets.token_hex(16)

def generate_user(token, broadcaster, timestamp):
    return {
        'token': token,
        'broadcaster': broadcaster,
        'name': None,
        'tripcode': None,
        'seen': {
            'first': timestamp,
            'last': timestamp,
        },
    }
