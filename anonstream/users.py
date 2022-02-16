import time
from math import inf

from quart import current_app

from anonstream.wrappers import with_timestamp, with_first_argument
from anonstream.utils.users import user_for_websocket
from anonstream.utils import listmap

def get_default_name(user):
    return (
        current_app.config['DEFAULT_HOST_NAME']
        if user['broadcaster'] else
        current_app.config['DEFAULT_ANON_NAME']
    )

def add_notice(user, notice):
    notice_id = time.time_ns() // 1_000_000
    user['notices'][notice_id] = notice
    if len(user['notices']) > current_app.config['LIMIT_NOTICES']:
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

def is_watching(timestamp, user):
    return user['watching_last'] >= timestamp - current_app.config['THRESHOLD_IDLE']

def is_idle(timestamp, user):
    return is_present(timestamp, user) and not is_watching(timestamp, user)

def is_present(timestamp, user):
    return user['seen']['last'] >= timestamp - current_app.config['THRESHOLD_ABSENT']

def is_absent(timestamp, user):
    return not is_present(timestamp, user)

def is_visible(timestamp, messages, user):
    has_visible_messages = any(
        message['token'] == user['token'] for message in messages
    )
    return has_visible_messages or is_present(timestamp, user)

last_checkup = -inf

def sunset(messages, users):
    global last_checkup

    timestamp = int(time.time())
    if timestamp - last_checkup < current_app.config['USER_CHECKUP_PERIOD']:
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
