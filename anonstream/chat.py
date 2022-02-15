from datetime import datetime

from quart import escape

class Rejected(Exception):
    pass

async def broadcast(websockets, payload):
    for queue in websockets:
        await queue.put(payload)

async def add_chat_message(chat, websockets, token, message_id, comment):
    # check message
    if len(comment) == 0:
        raise Rejected('Message was empty')

    # add message
    dt = datetime.utcnow()
    markup = escape(comment)
    chat[message_id] = {
        'id': message_id,
        'token': token,
        'timestamp': int(dt.timestamp()),
        'date': dt.strftime('%Y-%m-%d'),
        'time_minutes': dt.strftime('%H:%M'),
        'time_seconds': dt.strftime('%H:%M:%S'),
        'nomarkup': comment,
        'markup': markup,
    }

    # broadcast message to websockets
    await broadcast(
        websockets,
        payload={
            'type': 'chat',
            'color': '#c7007f',
            'name': 'Anonymous',
            'markup': markup,
        }
    )

    return markup
