from datetime import datetime

from quart import escape

def add_chat_message(chat, message_id, token, text):
    dt = datetime.utcnow()
    markup = escape(text)
    chat[message_id] = {
        'id': message_id,
        'token': token,
        'timestamp': int(dt.timestamp()),
        'date': dt.strftime('%Y-%m-%d'),
        'time_minutes': dt.strftime('%H:%M'),
        'time_seconds': dt.strftime('%H:%M:%S'),
        'nomarkup': text,
        'markup': markup,
    }
