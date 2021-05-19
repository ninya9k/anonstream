import base64
import io
import secrets
from captcha.image import ImageCaptcha
from website.constants import BACKGROUND_COLOUR, CAPTCHA_FONTS, CAPTCHA_SECRET_KEY
import werkzeug.security
import time
import base64
import math

CAPTCHA_CHARSET = '346qwertypagkxvbm'
CAPTCHA_LENGTH = 3
CAPTCHA = ImageCaptcha(width=72, height=30, fonts=CAPTCHA_FONTS, font_sizes=(24, 27, 30))

class FakeCiphertext(Exception):
    pass


class Incorrect(Exception):
    pass


def _image_to_base64(im):
    buffer = io.BytesIO()
    im.save(buffer, format='jpeg', quality=70)
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).rstrip(b'=')
    return (b'data:image/jpeg;base64,' + b64).decode()

def xor_bytes(data1, data2):
    return bytes(byte1 ^ byte2 for byte1, byte2 in zip(data1, data2))

def pbkdf2(salt, text):
    data = werkzeug.security._hash_internal('pbkdf2:sha256', salt, text)[0]
    data = bytes.fromhex(data)
    return data

def gen_captcha():
    answer = ''.join(secrets.choice(CAPTCHA_CHARSET) for _ in range(CAPTCHA_LENGTH))
    im = CAPTCHA.create_captcha_image(answer, (0xff, 0xff, 0xff), tuple(BACKGROUND_COLOUR))

    # current time in bytes
    now = int(time.time())
    n_bits = now.bit_length() + -now.bit_length() % 8
    now = f'{now:0{n_bits // 4}x}'
    now = bytes.fromhex(now)

    # create plaintext
    plaintext = b'\0' * 4 + now

    # create xor key
    key = pbkdf2(CAPTCHA_SECRET_KEY, answer)

    # create middletext
    middletext = xor_bytes(plaintext, key)

    # create ciphertext
    outer_key = pbkdf2(CAPTCHA_SECRET_KEY, middletext.hex())
    ciphertext = outer_key[:4] + middletext

    return _image_to_base64(im), base64.b64encode(ciphertext).decode()

def get_creation_time(ciphertext, answer):
    # get ciphertext
    try:
        ciphertext = base64.b64decode(ciphertext)
    except:
        raise FakeCiphertext

    # create middletext
    determinant = ciphertext[:4]
    middletext  = ciphertext[4:]
    outer_key = pbkdf2(CAPTCHA_SECRET_KEY, middletext.hex())
    if outer_key[:4] != determinant:
        raise FakeCiphertext

    # create xor key
    key = pbkdf2(CAPTCHA_SECRET_KEY, answer)

    # create plaintext
    plaintext = xor_bytes(middletext, key)

    determinant = int.from_bytes(plaintext[:4], 'big')
    timestamp   = int.from_bytes(plaintext[4:], 'big')

    # captcha answer was incorrect
    if determinant != 0:
        raise Incorrect(timestamp)

    return timestamp
