import time
from math import inf

from quart import current_app

from anonstream.wrappers import try_except_log, with_timestamp
from anonstream.helpers.user import is_visible
from anonstream.helpers.captcha import check_captcha_digest, Answer
from anonstream.helpers.tripcode import generate_tripcode
from anonstream.utils.colour import color_to_colour, get_contrast, NotAColor
from anonstream.utils.user import get_user_for_websocket

CONFIG = current_app.config
MESSAGES = current_app.messages
USERS = current_app.users
CAPTCHA_SIGNER = current_app.captcha_signer
USERS_UPDATE_BUFFER = current_app.users_update_buffer

class BadAppearance(ValueError):
    pass

class BadCaptcha(ValueError):
    pass

def add_state(user, **state):
    state_id = time.time_ns() // 1_000_000
    user['state'][state_id] = state
    while len(user['state']) > CONFIG['MAX_STATES']:
        user['state'].popitem(last=False)
    return state_id

def pop_state(user, state_id):
    try:
        state = user['state'].pop(state_id)
    except KeyError:
        state = None
    return state

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

        # Add to the users update buffer
        USERS_UPDATE_BUFFER.add(user['token'])

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
def get_all_users_for_websocket(timestamp):
    visible_users = filter(
        lambda user: is_visible(timestamp, MESSAGES, user),
        USERS,
    )
    return {
        user['token_hash']: get_user_for_websocket(user)
        for user in visible_users
    }

def verify(user, digest, answer):
    if user['verified']:
        verification_happened = False
    else:
        match check_captcha_digest(CAPTCHA_SIGNER, digest, answer):
            case Answer.MISSING:
                raise BadCaptcha('Captcha is required')
            case Answer.BAD:
                raise BadCaptcha('Captcha was incorrect')
            case Answer.EXPIRED:
                raise BadCaptcha('Captcha has expired')
            case Answer.OK:
                user['verified'] = True
                verification_happened = True

    return verification_happened

@with_timestamp
def deverify(timestamp, user):
    if not user['verified']:
        return

    n_user_messages = 0
    for message in reversed(MESSAGES):
        message_sent_ago = timestamp - message['timestamp']
        if message_sent_ago >= CONFIG['FLOOD_DURATION']:
            break
        elif message['token'] == user['token']:
            n_user_messages += 1

    if n_user_messages >= CONFIG['FLOOD_THRESHOLD']:
        user['verified'] = False
