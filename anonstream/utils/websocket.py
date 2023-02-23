# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum

WS = Enum('WS', names=('PONG', 'MESSAGE', 'CAPTCHA', 'APPEARANCE'))

class Malformed(Exception):
    pass

def get(t, pairs, key, default=None):
    value = pairs.get(key, default)
    if isinstance(value, t):
        return value
    else:
        raise Malformed(f'malformed {key}')

def parse_websocket_data(receipt):
    if not isinstance(receipt, dict):
        raise Malformed('not a json object')

    match receipt.get('type'):
        case 'message':
            form = get(dict, receipt, 'form')
            nonce = get(str, form, 'nonce')
            comment = get(str, form, 'comment')
            digest = get(str, form, 'captcha-digest', '')
            answer = get(str, form, 'captcha-answer', '')
            return WS.MESSAGE, (nonce, comment, digest, answer)

        case 'appearance':
            form = get(dict, receipt, 'form')
            name = get(str, form, 'name').strip()
            if len(name) == 0:
                name = None
            color = get(str, form, 'color')
            password = get(str, form, 'password')
            #match get(str | None, form, 'want-tripcode'):
            #    case '0':
            #        want_tripcode = False
            #    case '1':
            #        want_tripcode = True
            #    case _:
            #        want_tripcode = None
            want_tripcode = bool(password)
            return WS.APPEARANCE, (name, color, password, want_tripcode)

        case 'captcha':
            return WS.CAPTCHA, ()

        case 'pong':
            return WS.PONG, ()

        case _:
            raise Malformed('malformed type')
