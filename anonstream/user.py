import time
from math import inf

from quart import current_app

from anonstream.wrappers import with_timestamp, with_first_argument
from anonstream.helpers.user import is_visible
from anonstream.helpers.tripcode import generate_tripcode
from anonstream.utils.colour import color_to_colour, get_contrast, NotAColor
from anonstream.utils.user import user_for_websocket

CONFIG = current_app.config

class BadAppearance(Exception):
    pass

def add_notice(user, notice, verbose=False):
    notice_id = time.time_ns() // 1_000_000
    user['notices'][notice_id] = (notice, verbose)
    if len(user['notices']) > CONFIG['MAX_NOTICES']:
        user['notices'].popitem(last=False)
    return notice_id

def pop_notice(user, notice_id):
    try:
        notice, verbose = user['notices'].pop(notice_id)
    except KeyError:
        notice, verbose = None, False
    return notice, verbose

def change_name(user, name, dry_run=False):
    if dry_run:
        if name is not None:
            if len(name) == 0:
                raise BadAppearance('Name was empty')
            if len(name) > 24:
                raise BadAppearance('Name exceeded 24 chars')
    else:
        user['name'] = name

def change_color(user, color, dry_run=False):
    if dry_run:
        try:
            colour = color_to_colour(color)
        except NotAColor:
            raise BadAppearance('Invalid CSS color')
        contrast = get_contrast(
            CONFIG['CHAT_BACKGROUND_COLOUR'],
            colour,
        )
        min_contrast = CONFIG['CHAT_NAME_MIN_CONTRAST']
        if contrast < min_contrast:
            raise BadAppearance(
                'Colour had insufficient contrast:',
                (f'{contrast:.2f}', f'/{min_contrast}'),
            )
    else:
        user['color'] = color

def change_tripcode(user, password, dry_run=False):
    if dry_run:
        if len(password) > 1024:
            raise BadAppearance('Password exceeded 1024 chars')
    else:
        user['tripcode'] = generate_tripcode(password)

def delete_tripcode(user):
    user['tripcode'] = None

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
    if timestamp - last_checkup < CONFIG['CHECKUP_PERIOD_USER']:
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
