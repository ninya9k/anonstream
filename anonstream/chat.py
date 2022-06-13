# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import time
from datetime import datetime

from quart import current_app, escape

from anonstream.broadcast import broadcast, broadcast_users_update
from anonstream.helpers.chat import generate_nonce_hash, get_scrollback
from anonstream.utils.chat import get_message_for_websocket, get_approx_linespan

CONFIG = current_app.config
MESSAGES_BY_ID = current_app.messages_by_id
MESSAGES = current_app.messages
USERS_BY_TOKEN = current_app.users_by_token
USERS = current_app.users

class Rejected(ValueError):
    pass

def get_all_messages_for_websocket():
    return list(map(
        lambda message: get_message_for_websocket(
            user=USERS_BY_TOKEN[message['token']],
            message=message,
        ),
        get_scrollback(MESSAGES),
    ))

def add_chat_message(user, nonce, comment, ignore_empty=False):
    # Special case: if the comment is empty, do nothing and return
    if ignore_empty and len(comment) == 0:
        return False

    timestamp_ms = time.time_ns() // 1_000_000
    timestamp = timestamp_ms // 1000

    # Check user
    while user['linespan']:
        linespan_timestamp, _ = user['linespan'][0]
        if timestamp - linespan_timestamp >= CONFIG['FLOOD_LINE_DURATION']:
            user['linespan'].popleft()
        else:
            break
    total_recent_linespan = sum(map(
        lambda linespan_tuple: linespan_tuple[1],
        user['linespan'],
    ))
    if total_recent_linespan > CONFIG['FLOOD_LINE_THRESHOLD']:
        raise Rejected(
            f'Chat overuse in the last '
            f'{CONFIG["FLOOD_LINE_DURATION"]:.0f} seconds'
        )

    # Check message
    message_id = generate_nonce_hash(nonce)
    if message_id in MESSAGES_BY_ID:
        raise Rejected('Discarded suspected duplicate message')
    if len(comment) == 0:
        raise Rejected('Message was empty')
    if len(comment.strip()) == 0:
        raise Rejected('Message was practically empty')
    if len(comment) > 512:
        raise Rejected('Message exceeded 512 chars')
    if comment.count('\n') + 1 > 12:
        raise Rejected('Message exceeded 12 lines')

    linespan = get_approx_linespan(comment)
    if linespan > 12:
        raise Rejected('Message would span too many lines')

    # Record linespan
    linespan_tuple = (timestamp, linespan)
    user['linespan'].append(linespan_tuple)

    # Create and add message
    try:
        last_message = next(reversed(MESSAGES))
    except StopIteration:
        seq = timestamp_ms
    else:
        if timestamp_ms > last_message['seq']:
            seq = timestamp_ms
        else:
            seq = last_message['seq'] + 1
    dt = datetime.utcfromtimestamp(timestamp)
    markup = escape(comment)
    message = {
        'id': message_id,
        'seq': seq,
        'token': user['token'],
        'timestamp': timestamp,
        'date': dt.strftime('%Y-%m-%d'),
        'time_minutes': dt.strftime('%H:%M'),
        'time_seconds': dt.strftime('%H:%M:%S'),
        'nomarkup': comment,
        'markup': markup,
    }
    MESSAGES_BY_ID[message_id] = message

    while len(MESSAGES_BY_ID) > CONFIG['MAX_CHAT_MESSAGES']:
        MESSAGES_BY_ID.pop(last=False)

    # Broadcast a users update to all websockets,
    # in case this message is from a new user
    broadcast_users_update()

    # Broadcast message to websockets
    broadcast(
        USERS,
        payload={
            'type': 'message',
            'message': get_message_for_websocket(user, message),
        },
    )

    return True

def delete_chat_messages(seqs):
    seq_set = set(seqs)
    message_ids = set()
    for message_id, message in MESSAGES_BY_ID.items():
        if len(seq_set) == 0:
            break
        try:
            seq_set.remove(message['seq'])
        except KeyError:
            pass
        else:
            message_ids.add(message_id)
    for message_id in message_ids:
        MESSAGES_BY_ID.pop(message_id)
    broadcast(
        USERS,
        payload={
            'type': 'delete',
            'seqs': seqs,
        },
    )
