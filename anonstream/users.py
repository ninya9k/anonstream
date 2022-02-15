import time

from quart import current_app

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
