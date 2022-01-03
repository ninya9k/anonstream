import werkzeug.security
import base64
import website.utils.colour
from website.constants import BACKGROUND_COLOUR, CONFIG

FOREGROUND_COLOURS = (b'\0\0\0', b'\x3f\x3f\x3f', b'\x7f\x7f\x7f', b'\xbf\xbf\xbf', b'\xff\xff\xff')

def default():
    return {'string': None, 'background_colour': None, 'foreground_colour': None}

def tripcode_salt():
    return CONFIG['secrets']['tripcode_salt'] or '\0'

def gen_tripcode(password):
    tripcode = default()
    pwhash = werkzeug.security._hash_internal('pbkdf2:sha256:150000', tripcode_salt(), password)[0]
    tripcode_data = bytes.fromhex(pwhash)[:6]
    tripcode['string'] = base64.b64encode(tripcode_data).decode()
    tripcode['background_colour'] = website.utils.colour.gen_colour(tripcode_data, BACKGROUND_COLOUR)
    tripcode['foreground_colour'] = max(FOREGROUND_COLOURS, key=lambda c: website.utils.colour._distance_sq(c, tripcode['background_colour']))
    return tripcode
