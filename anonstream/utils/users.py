import secrets
from collections import OrderedDict

def generate_token():
    return secrets.token_hex(16)

def generate_user(token, broadcaster, timestamp):
    return {
        'token': token,
        'broadcaster': broadcaster,
        'name': None,
        'tripcode': None,
        'notices': OrderedDict(),
        'seen': {
            'first': timestamp,
            'last': timestamp,
        },
    }
