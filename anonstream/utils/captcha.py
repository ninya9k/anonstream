# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib

from captcha.image import ImageCaptcha
from itsdangerous import TimestampSigner

def create_captcha_factory(fonts):
    return ImageCaptcha(
        width=72,
        height=30,
        fonts=fonts,
        font_sizes=(24, 27, 30),
    )

def create_captcha_signer(secret_key):
    return TimestampSigner(
        secret_key=secret_key,
        salt=b'captcha-signature',
        digest_method=hashlib.sha256,
    )
