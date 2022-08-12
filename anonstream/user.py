# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import operator
import time
from functools import reduce
from math import inf

from quart import current_app

from anonstream.events import notify_event_sockets
from anonstream.wrappers import try_except_log, with_timestamp, get_timestamp
from anonstream.helpers.user import get_default_name, get_presence, Presence
from anonstream.helpers.captcha import check_captcha_digest, Answer
from anonstream.helpers.tripcode import generate_tripcode
from anonstream.utils.colour import color_to_colour, get_contrast, NotAColor
from anonstream.utils.user import get_user_for_websocket, trilean

CONFIG = current_app.config
MESSAGES = current_app.messages
USERS = current_app.users
ALLOWEDNESS = current_app.allowedness
CAPTCHA_SIGNER = current_app.captcha_signer
USERS_UPDATE_BUFFER = current_app.users_update_buffer

class BadAppearance(ValueError):
    pass

class BadCaptcha(ValueError):
    pass

class EyesException(Exception):
    pass

class TooManyEyes(EyesException):
    pass

class RatelimitedEyes(EyesException):
    pass

class DeletedEyes(EyesException):
    pass

class ExpiredEyes(EyesException):
    pass

class DisallowedEyes(EyesException):
    pass

class AllowednessException(Exception):
    pass

class Blacklisted(AllowednessException):
    pass

class SecretClub(AllowednessException):
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

def try_change_appearance(user, name, color, password, want_tripcode):
    errors = []
    def try_(f, *args, **kwargs):
        return try_except_log(errors, BadAppearance)(f)(*args, **kwargs)

    try_(change_name, user, name, dry_run=True)
    try_(change_color, user, color, dry_run=True)
    if want_tripcode:
        try_(change_tripcode, user, password, dry_run=True)

    if not errors:
        change_name(user, name)
        change_color(user, color)

        # Leave tripcode
        if want_tripcode is None:
            pass

        # Delete tripcode
        elif not want_tripcode:
            delete_tripcode(user)

        # Change tripcode
        elif want_tripcode:
            change_tripcode(user, password)

        # Add to the users update buffer
        USERS_UPDATE_BUFFER.add(user['token'])

        # Notify event sockets that a user's appearance was set
        # NOTE: Changing appearance is currently NOT ratelimited.
        #       Applications using the event socket API should buffer these
        #       events or do something else to a prevent a potential denial of
        #       service.
        notify_event_sockets({
            'type': 'appearance',
            'event': {
                'token': user['token'],
                'name': user['name'],
                'color': user['color'],
                'tripcode': user['tripcode'],
            }
        })

    return errors

def change_name(user, name, dry_run=False):
    if dry_run:
        if name == get_default_name(user):
            name = None
        if name is not None:
            if len(name) == 0:
                raise BadAppearance('Name was empty')
            if len(name) > CONFIG['CHAT_NAME_MAX_LENGTH']:
                raise BadAppearance(
                    f'Name exceeded {CONFIG["CHAT_NAME_MAX_LENGTH"]} chars'
                )
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
                (f'{contrast:.2f}', f'/{min_contrast:.2f}'),
            )
    else:
        user['color'] = color

def change_tripcode(user, password, dry_run=False):
    if dry_run:
        if len(password) > CONFIG['CHAT_TRIPCODE_PASSWORD_MAX_LENGTH']:
            raise BadAppearance(
                f'Password exceeded '
                f'{CONFIG["CHAT_TRIPCODE_PASSWORD_MAX_LENGTH"]} chars'
            )
    else:
        user['tripcode'] = generate_tripcode(password)

def delete_tripcode(user):
    user['tripcode'] = None

def see(user, timestamp=None):
    if timestamp is None:
        timestamp = get_timestamp()
    user['last']['seen'] = timestamp

def watching(user, timestamp=None):
    if timestamp is None:
        timestamp = get_timestamp()
    user['last']['seen'] = timestamp
    user['last']['watching'] = timestamp

def reading(user, timestamp=None):
    if timestamp is None:
        timestamp = get_timestamp()
    user['last']['seen'] = timestamp
    user['last']['reading'] = timestamp

@with_timestamp()
def get_all_users_for_websocket(timestamp):
    return {
        user['token_hash']: get_user_for_websocket(user)
        for user in get_unsunsettable_users(timestamp)
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

def deverify(user, timestamp=None):
    '''
    Try to deverify a user. The user is deverified iff they have
    exceeded the message flood threshold.
    '''
    if timestamp is None:
        timestamp = get_timestamp()
    if user['verified'] and not user['broadcaster']:
        n_user_messages = 0
        for message in reversed(MESSAGES):
            message_sent_ago = timestamp - message['timestamp']
            if message_sent_ago >= CONFIG['FLOOD_MESSAGE_DURATION']:
                break
            elif message['token'] == user['token']:
                n_user_messages += 1
        if n_user_messages >= CONFIG['FLOOD_MESSAGE_THRESHOLD']:
            user['verified'] = False

def _update_presence(timestamp, user):
    old, user['presence'] = user['presence'], get_presence(timestamp, user)
    if trilean(user['presence']) != trilean(old):
        USERS_UPDATE_BUFFER.add(user['token'])
    return user['presence']

@with_timestamp()
def update_presence(timestamp, user):
    return _update_presence(timestamp, user)

def get_users_and_update_presence(timestamp):
    for user in USERS:
        _update_presence(timestamp, user)
        yield user

def get_watching_users(timestamp):
    return filter(
        lambda user: user['presence'] == Presence.WATCHING,
        get_users_and_update_presence(timestamp),
    )

def get_absent_users(timestamp):
    return filter(
        lambda user: user['presence'] == Presence.ABSENT,
        get_users_and_update_presence(timestamp),
    )

def is_sunsettable(user):
    return user['presence'] == Presence.ABSENT and not has_left_messages(user)

def has_left_messages(user):
    return any(
        message['token'] == user['token']
        for message in MESSAGES
    )

def get_sunsettable_users(timestamp):
    return filter(
        is_sunsettable,
        get_users_and_update_presence(timestamp),
    )

def get_unsunsettable_users(timestamp):
    return filter(
        lambda user: not is_sunsettable(user),
        get_users_and_update_presence(timestamp),
    )

@with_timestamp()
def get_users_by_presence(timestamp):
    users_by_presence = {
        Presence.WATCHING: [],
        Presence.NOTWATCHING: [],
        Presence.TENTATIVE: [],
        Presence.ABSENT: [],
    }
    for user in get_users_and_update_presence(timestamp):
        users_by_presence[user['presence']].append(user)
    return users_by_presence

@with_timestamp(precise=True)
def create_eyes(timestamp, user, headers):
    # Unlike in renew_eyes, allowedness is NOT checked here because it is
    # assumed to have already been checked (by the route handler).

    # Enforce cooldown
    last_created_ago = timestamp - user['last']['eyes']
    cooldown_ended_ago = last_created_ago - CONFIG['FLOOD_VIDEO_COOLDOWN']
    cooldown_remaining = -cooldown_ended_ago
    if cooldown_remaining > 0:
        raise RatelimitedEyes(cooldown_remaining)

    # Enforce max_eyes & overwrite
    if len(user['eyes']['current']) >= CONFIG['FLOOD_VIDEO_MAX_EYES']:
        # Treat eyes as a stack, do not create new eyes if it would
        # cause the limit to be exceeded
        if not CONFIG['FLOOD_VIDEO_OVERWRITE']:
            raise TooManyEyes(len(user['eyes']['current']))
        # Treat eyes as a queue, expire old eyes upon creating new eyes
        # if the limit would have been exceeded otherwise
        elif user['eyes']['current']:
            oldest_eyes_id = min(user['eyes']['current'])
            user['eyes']['current'].pop(oldest_eyes_id)

    # Create eyes
    eyes_id = user['eyes']['total']
    user['eyes']['total'] += 1
    user['last']['eyes'] = timestamp
    user['eyes']['current'][eyes_id] = {
        'id': eyes_id,
        'token': user['token'],
        'n_segments': 0,
        'headers': headers,
        'created': timestamp,
        'renewed': timestamp,
    }
    return eyes_id

def renew_eyes(timestamp, user, eyes_id, just_read_new_segment=False):
    try:
        eyes = user['eyes']['current'][eyes_id]
    except KeyError as e:
        raise DeletedEyes from e

    # Enforce expire_after (if the background task hasn't already)
    renewed_ago = timestamp - eyes['renewed']
    if renewed_ago >= CONFIG['FLOOD_VIDEO_EYES_EXPIRE_AFTER']:
        user['eyes']['current'].pop(eyes_id)
        raise ExpiredEyes

    # Ensure allowedness
    try:
        ensure_allowedness(user, timestamp=timestamp)
    except AllowednessException as e:
        user['eyes']['current'].pop(eyes_id)
        raise DisallowedEyes from e

    if just_read_new_segment:
        eyes['n_segments'] += 1
    eyes['renewed'] = timestamp

def ensure_allowedness(user, timestamp=None):
    if timestamp is None:
        timestamp = get_timestamp()

    # Check against blacklist
    for keytuple, values in ALLOWEDNESS['blacklist'].items():
        try:
            value = reduce(lambda mapping, key: mapping[key], keytuple, user)
        except (KeyError, TypeError):
            value = None
        if value in values:
            raise Blacklisted

    # Check against whitelist
    for keytuple, values in ALLOWEDNESS['whitelist'].items():
        try:
            value = reduce(lambda mapping, key: mapping[key], keytuple, user)
        except (KeyError, TypeError):
            value = None
        if value in values:
            break
    else:
        # Apply default
        if not ALLOWEDNESS['default']:
            raise SecretClub

    user['last']['allowed'] = timestamp
