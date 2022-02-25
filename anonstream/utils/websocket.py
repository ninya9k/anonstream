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
            return nonce, comment, digest, answer

        case 'appearance':
            raise NotImplemented

        case 'captcha':
            return None

        case _:
            raise Malformed('malformed type')
