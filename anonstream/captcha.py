# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import secrets

from quart import current_app

from anonstream.helpers.captcha import generate_captcha_digest, generate_captcha_image

CONFIG = current_app.config
CAPTCHAS = current_app.captchas
CAPTCHA_FACTORY = current_app.captcha_factory
CAPTCHA_SIGNER = current_app.captcha_signer

def generate_random_captcha_solution():
    return ''.join(
        secrets.choice(CONFIG['CAPTCHA_ALPHABET'])
        for _ in range(CONFIG['CAPTCHA_LENGTH'])
    )

def _get_random_cached_captcha_digest():
    chosen_index = secrets.randbelow(len(CAPTCHAS))
    for index, digest in enumerate(CAPTCHAS):
        if index == chosen_index:
            break
    return digest

def get_random_captcha_digest():
    if len(CAPTCHAS) >= CONFIG['MAX_CAPTCHAS']:
        digest = _get_random_cached_captcha_digest()
    else:
        salt = secrets.token_bytes(16)
        solution = generate_random_captcha_solution()
        digest = generate_captcha_digest(CAPTCHA_SIGNER, salt, solution)
        CAPTCHAS[digest] = {'solution': solution}
        while len(CAPTCHAS) >= CONFIG['MAX_CAPTCHAS']:
            CAPTCHAS.popitem(last=False)

    return digest

def get_random_captcha_digest_for(user):
    if user['verified']:
        return None
    else:
        return get_random_captcha_digest()

def get_captcha_image(digest):
    try:
        captcha = CAPTCHAS[digest]
    except KeyError:
        return None
    else:
        if 'image' not in captcha:
            captcha['image'] = generate_captcha_image(
                factory=CAPTCHA_FACTORY,
                solution=captcha.pop('solution'),
            )
        return captcha['image']
