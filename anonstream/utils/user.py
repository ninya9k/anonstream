import base64
import hashlib
import secrets
from collections import OrderedDict
from math import inf

from quart import escape, Markup

def generate_token():
    return secrets.token_hex(16)

def get_user_for_websocket(user):
    keys = ['broadcaster', 'name', 'color', 'tripcode']
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
