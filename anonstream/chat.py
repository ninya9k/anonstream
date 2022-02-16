import time
from datetime import datetime

from quart import escape

from anonstream.users import users_for_websocket
from anonstream.utils.chat import generate_nonce_hash

class Rejected(Exception):
    pass

async def broadcast(websockets, payload):
    for queue in websockets:
        await queue.put(payload)

async def add_chat_message(chat, users, websockets, secret, user, nonce, comment):
    # check message
    nonce_hash = generate_nonce_hash(secret, nonce)
    if nonce_hash in chat['nonce_hashes']:
        raise Rejected('Discarded suspected duplicate message')
    if len(comment) == 0:
        raise Rejected('Message was empty')

    # add message
    timestamp_ms = time.time_ns() // 1_000_000
    timestamp = timestamp_ms // 1000
    try:
        last_message = next(reversed(chat['messages'].values()))
    except StopIteration:
        message_id = timestamp_ms
    else:
        if timestamp <= last_message['id']:
            message_id = last_message['id'] + 1
    dt = datetime.utcfromtimestamp(timestamp)
    markup = escape(comment)
    chat['messages'][message_id] = {
        'id': message_id,
        'nonce_hash': nonce_hash,
        'token': user['token'],
        'timestamp': timestamp,
        'date': dt.strftime('%Y-%m-%d'),
        'time_minutes': dt.strftime('%H:%M'),
        'time_seconds': dt.strftime('%H:%M:%S'),
        'nomarkup': comment,
        'markup': markup,
    }

    # collect nonce hash
    chat['nonce_hashes'].add(nonce_hash)

    # broadcast message to websockets
    await broadcast(
        websockets,
        payload={
            'type': 'chat',
            'id': message_id,
            'token_hash': user['token_hash'],
            'markup': markup,
        }
    )

    return markup
