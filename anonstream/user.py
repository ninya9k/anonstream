import time
from math import inf

from quart import current_app

from anonstream.wrappers import with_timestamp, with_first_argument
from anonstream.helpers.user import is_visible
from anonstream.utils.user import user_for_websocket
from anonstream.utils import listmap

CONFIG = current_app.config

def add_notice(user, notice):
    notice_id = time.time_ns() // 1_000_000
    user['notices'][notice_id] = notice
    if len(user['notices']) > CONFIG['MAX_NOTICES']:
        user['notices'].popitem(last=False)
    return notice_id

def pop_notice(user, notice_id):
    try:
        notice = user['notices'].pop(notice_id)
    except KeyError:
        notice = None
    return notice

def see(user):
    user['seen']['last'] = int(time.time())

@with_timestamp
def users_for_websocket(timestamp, messages, users):
    visible_users = filter(
        lambda user: is_visible(timestamp, messages, user),
        users.values(),
    )
    return {
        user['token_hash']: user_for_websocket(user, include_token_hash=False)
        for user in visible_users
    }

last_checkup = -inf

def sunset(messages, users):
    global last_checkup

    timestamp = int(time.time())
    if timestamp - last_checkup < CONFIG['USER_CHECKUP_PERIOD']:
        return []

    to_delete = []
    for token in users:
        user = users[token]
        if not is_visible(timestamp, messages, user):
            to_delete.append(token)

    for index, token in enumerate(to_delete):
        to_delete[index] = users.pop(token)['token_hash']

    last_checkup = timestamp
    return to_delete
