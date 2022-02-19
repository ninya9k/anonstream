import time
from math import inf

from quart import current_app

from anonstream.chat import broadcast
from anonstream.wrappers import try_except_log, with_timestamp
from anonstream.helpers.user import is_visible
from anonstream.helpers.tripcode import generate_tripcode
from anonstream.utils.colour import color_to_colour, get_contrast, NotAColor
from anonstream.utils.user import user_for_websocket

CONFIG = current_app.config
MESSAGES = current_app.messages
USERS = current_app.users

class BadAppearance(Exception):
    pass

def add_notice(user, notice, verbose=False):
    notice_id = time.time_ns() // 1_000_000
    user['notices'][notice_id] = (notice, verbose)
    while len(user['notices']) > CONFIG['MAX_NOTICES']:
        user['notices'].popitem(last=False)
    return notice_id

def pop_notice(user, notice_id):
    try:
        notice, verbose = user['notices'].pop(notice_id)
    except KeyError:
        notice, verbose = None, False
    return notice, verbose

def try_change_appearance(user, name, color, password,
                          want_delete_tripcode, want_change_tripcode):
    errors = []
    def try_(f, *args, **kwargs):
        return try_except_log(errors, BadAppearance)(f)(*args, **kwargs)

    try_(change_name, user, name, dry_run=True)
    try_(change_color, user, color, dry_run=True)
    if want_delete_tripcode:
        pass
    elif want_change_tripcode:
        try_(change_tripcode, user, password, dry_run=True)

    if not errors:
        change_name(user, name)
        change_color(user, color)
        if want_delete_tripcode:
            delete_tripcode(user)
        elif want_change_tripcode:
            change_tripcode(user, password)

        broadcast(
            USERS,
            payload={
                'type': 'mut-user',
                'token_hash': user['token_hash'],
                'name': user['name'],
                'color': user['color'],
                'tripcode': user['tripcode'],
            },
        )

    return errors

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
    user['last']['seen'] = int(time.time())

@with_timestamp
def users_for_websocket(timestamp):
    visible_users = filter(
        lambda user: is_visible(timestamp, MESSAGES, user),
        USERS,
    )
    return {
        user['token_hash']: user_for_websocket(user)
        for user in visible_users
    }
