from anonstream.utils.chat import generate_message_id

def parse(message_ids, secret, receipt):
    if not isinstance(receipt, dict):
        return None, 'not a json object'

    message = receipt.get('message')
    if not isinstance(message, str):
        return None, 'malformed chat message'

    nonce = receipt.get('nonce')
    if not isinstance(nonce, str):
        return None, 'malformed nonce'

    message_id = generate_message_id(secret, nonce)
    if message_id in message_ids:
        return None, 'nonce already used'

    return (message, nonce, message_id), None
