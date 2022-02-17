import base64
import hashlib

import werkzeug.security
from quart import current_app

from anonstream.utils.colour import generate_colour, generate_maximum_contrast_colour, colour_to_color

CONFIG = current_app.config

def _generate_tripcode_digest_legacy(password):
    hexdigest, _ = werkzeug.security._hash_internal(
        'pbkdf2:sha256:150000',
        CONFIG['SECRET_KEY'],
        password,
    )
    digest = bytes.fromhex(hexdigest)
    return base64.b64encode(digest)[:8].decode()

def generate_tripcode_digest(password):
    parts = CONFIG['SECRET_KEY'] + b'tripcode\0' + password.encode()
    digest = hashlib.sha256(parts).digest()
    return base64.b64encode(digest)[:8].decode()

def generate_tripcode(password, generate_digest=generate_tripcode_digest):
    digest = generate_digest(password)
    background_colour = generate_colour(
        seed='tripcode-background\0' + digest,
        bg=CONFIG['CHAT_BACKGROUND_COLOUR'],
        contrast=5.0,
    )
    foreground_colour = generate_maximum_contrast_colour(
        seed='tripcode-foreground\0' + digest,
        bg=background_colour,
    )
    return {
        'digest': digest,
        'background_color': colour_to_color(background_colour),
        'foreground_color': colour_to_color(foreground_colour),
    }
