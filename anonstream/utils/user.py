import base64
import hashlib
import secrets
from collections import OrderedDict
from math import inf

from quart import escape, Markup

def generate_token():
    return secrets.token_hex(16)

def user_for_websocket(user, include_token_hash=True):
    keys = ['broadcaster', 'name', 'color', 'tripcode']
    if include_token_hash:
        keys.append('token_hash')
    return {key: user[key] for key in keys}

def concatenate_for_notice(string, *tuples):
    if not tuples:
        return string
    markup = Markup(
        ''.join(
            f' <mark>{escape(x)}</mark>{escape(y)}'
            for x, y in tuples
        )
    )
    return string + markup
