# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import hashlib

import werkzeug.security
from quart import current_app

from anonstream.utils.colour import generate_colour, generate_maximum_contrast_colour, colour_to_color

CONFIG = current_app.config

def _generate_tripcode_digest_legacy(password):
    hexdigest, _ = werkzeug.security._hash_internal(
        'pbkdf2:sha256:150000',
        CONFIG['SECRET_KEY_STRING'],
        password,
    )
    digest = bytes.fromhex(hexdigest)
    return base64.b64encode(digest)[:8].decode()

def _generate_tripcode_digest(password):
    parts = CONFIG['SECRET_KEY'] + b'tripcode\0' + password.encode()
    digest = hashlib.sha256(parts).digest()
    return base64.b64encode(digest)[:8].decode()

def generate_tripcode_digest(password):
    algorithm = (
        _generate_tripcode_digest_legacy
        if CONFIG['CHAT_LEGACY_TRIPCODE_ALGORITHM'] else
        _generate_tripcode_digest
    )
    return algorithm(password)

def generate_tripcode(password):
    digest = generate_tripcode_digest(password)
    background_colour = generate_colour(
        seed='tripcode-background\0' + digest,
        bg=CONFIG['CHAT_BACKGROUND_COLOUR'],
        min_contrast=5.0,
        max_contrast=5.0,
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
