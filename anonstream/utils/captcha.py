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
