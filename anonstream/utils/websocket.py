class Malformed(Exception):
    pass

def parse_websocket_data(receipt):
    if not isinstance(receipt, dict):
        raise Malformed('not a json object')

    comment = receipt.get('comment')
    if not isinstance(comment, str):
        raise Malformed('malformed comment')

    nonce = receipt.get('nonce')
    if not isinstance(nonce, str):
        raise Malformed('malformed nonce')

    return nonce, comment
