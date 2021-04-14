import base64
import io
import secrets
from captcha.image import ImageCaptcha
from website.constants import CONFIG, BACKGROUND_COLOUR

CAPTCHA_CHARSET = '346qwertypagkxvbm'
CAPTCHA_LENGTH = 3
CAPTCHA = ImageCaptcha(width=72, height=30, fonts=CONFIG['fonts'], font_sizes=(24, 27, 30))

def _image_to_base64(im):
    buffer = io.BytesIO()
    im.save(buffer, format='jpeg', quality=70)
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).rstrip(b'=')
    return (b'data:image/jpeg;base64,' + b64).decode()

def gen_captcha():
    answer = ''.join(secrets.choice(CAPTCHA_CHARSET) for _ in range(CAPTCHA_LENGTH))
    im = CAPTCHA.create_captcha_image(answer, (0xff, 0xff, 0xff), tuple(BACKGROUND_COLOUR))
    return _image_to_base64(im), answer