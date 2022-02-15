from anonstream.utils.chat import create_message, NonceReuse

class Malformed(Exception):
    pass

def parse_websocket_data(message_ids, secret, receipt):
    if not isinstance(receipt, dict):
        raise Malformed('not a json object')

    comment = receipt.get('comment')
    if not isinstance(comment, str):
        raise Malformed('malformed comment')

    nonce = receipt.get('nonce')
    if not isinstance(nonce, str):
        raise Malformed('malformed nonce')

    try:
        message = create_message(message_ids, secret, nonce, comment)
    except NonceReuse:
        raise Malformed('nonce already used')

    return message
