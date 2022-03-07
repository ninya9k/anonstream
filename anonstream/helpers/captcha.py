# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import binascii
import hashlib
import io
from enum import Enum

from itsdangerous import TimestampSigner
from itsdangerous.exc import BadSignature, SignatureExpired
from quart import current_app

CONFIG = current_app.config

Answer = Enum('Answer', names=('OK', 'EXPIRED', 'BAD', 'MISSING'))

def generate_captcha_image(factory, solution):
    im = factory.create_captcha_image(
        solution,
        CONFIG['CAPTCHA_FOREGROUND_COLOUR'],
        CONFIG['CAPTCHA_BACKGROUND_COLOUR'],
    )
    buffer = io.BytesIO()
    im.save(buffer, format='jpeg', quality=75, optimize=True)
    buffer.seek(0)
    return buffer.read()

def _generate_captcha_unsigned_digest(salt, solution):
    parts = (
        CONFIG['SECRET_KEY']
        + b'captcha-digest\0'
        + salt
        + solution.encode()
    )
    raw_unsigned_digest = hashlib.sha256(parts).digest()[:16] + salt
    return base64.urlsafe_b64encode(raw_unsigned_digest).removesuffix(b'=')

def generate_captcha_digest(signer, salt, solution):
    unsigned_digest = _generate_captcha_unsigned_digest(salt, solution)
    return signer.sign(unsigned_digest).decode()

def check_captcha_digest(signer, digest, answer):
    if len(answer) == 0:
        result = Answer.MISSING
    else:
        try:
            unsigned_digest = signer.unsign(
                digest,
                max_age=CONFIG['CAPTCHA_LIFETIME'],
            )
        except SignatureExpired:
            result = Answer.EXPIRED
        except BadSignature:
            result = Answer.BAD
        else:
            try:
                raw_unsigned_digest = (
                    base64.urlsafe_b64decode(unsigned_digest + b'=')
                )
            except binascii.Error:
                result = Answer.BAD
            else:
                salt = raw_unsigned_digest[16:]
                true_unsigned_digest = (
                    _generate_captcha_unsigned_digest(salt, answer)
                )
                if unsigned_digest == true_unsigned_digest:
                    result = Answer.OK
                else:
                    result = Answer.BAD

    return result
