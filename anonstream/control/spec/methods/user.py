# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from quart import current_app

from anonstream.control.exceptions import CommandFailed
from anonstream.control.spec.common import Str, End, ArgsInt, ArgsString, ArgsJson, ArgsJsonBoolean, ArgsJsonString, ArgsUser
from anonstream.control.spec.utils import json_dumps_contiguous
from anonstream.utils.user import USER_WEBSOCKET_ATTRS
from anonstream.routes.wrappers import generate_and_add_user
from anonstream.wrappers import get_timestamp

USERS_BY_TOKEN = current_app.users_by_token
USERS_UPDATE_BUFFER = current_app.users_update_buffer

async def cmd_user_help():
    normal = ['user', 'help']
    response = (
            'Usage: user [show | attr USER | get USER ATTR | set USER ATTR VALUE]\n'
            'Commands:\n'
            ' user [show]...................show all users\' tokens\n'
            ' user attr USER................show names of a user\'s attributes\n'
            ' user get USER ATTR............show an attribute of a user\n'
            ' user set USER ATTR VALUE......set an attribute of a user\n'
            ' user eyes USER [show].........show a user\'s active video responses\n'
            ' user eyes USER delete EYES_ID.end a video response to a user\n'
            ' user add VERIFIED TOKEN.......add new user\n'
            'Definitions:\n'
            ' USER..........................={token TOKEN | hash HASH}\n'
            ' TOKEN.........................a token, json string\n'
            ' HASH..........................a token hash\n'
            ' ATTR..........................a user attribute, re:[a-z0-9_]+\n'
            ' VALUE.........................json value\n'
            ' EYES_ID.......................a user\'s eyes_id, base 10 integer\n'
            ' VERIFIED......................user\'s verified state: true = normal, false = can\'t chat, null = will be kicked to access captcha\n'
    )
    return normal, response

async def cmd_user_show():
    normal = ['user', 'show']
    response = json.dumps(tuple(USERS_BY_TOKEN)) + '\n'
    return normal, response

async def cmd_user_attr(user):
    normal = ['user', 'attr', 'token', json_dumps_contiguous(user['token'])]
    response = json.dumps(tuple(user.keys())) + '\n'
    return normal, response

async def cmd_user_get(user, attr):
    try:
        value = user[attr]
    except KeyError as e:
        raise CommandFailed('user has no such attribute') from e
    try:
        value_json = json.dumps(value)
    except (TypeError, ValueError) as e:
        raise CommandFailed('value is not representable in json') from e
    normal = [
        'user',
        'get',
        'token',
        json_dumps_contiguous(user['token']),
        attr,
    ]
    response = value_json + '\n'
    return normal, response

async def cmd_user_set(user, attr, value):
    if attr not in user:
        raise CommandFailed(f'user has no attribute {attr!r}')
    user[attr] = value
    if attr in USER_WEBSOCKET_ATTRS:
        USERS_UPDATE_BUFFER.add(user['token'])
    normal = [
        'user',
        'set',
        'token',
        json_dumps_contiguous(user['token']),
        attr,
        json_dumps_contiguous(value),
    ]
    response = ''
    return normal, response

async def cmd_user_eyes_show(user):
    normal = [
        'user',
        'eyes',
        'token',
        json_dumps_contiguous(user['token']),
        'show'
    ]
    response = json.dumps(user['eyes']['current']) + '\n'
    return normal, response

async def cmd_user_eyes_delete(user, eyes_id):
    try:
        user['eyes']['current'].pop(eyes_id)
    except KeyError:
        pass
    normal = [
        'user',
        'eyes',
        'token',
        json_dumps_contiguous(user['token']),
        'delete',
        str(eyes_id),
    ]
    response = ''
    return normal, response

async def cmd_user_add(verified, token):
    if token in USERS_BY_TOKEN:
        raise CommandFailed(f'user with token {token!r} already exists')
    _user = generate_and_add_user(
        timestamp=get_timestamp(),
        token=token,
        verified=verified,
    )
    normal = [
        'user', 'add',
        json_dumps_contiguous(verified), json_dumps_contiguous(token),
    ]
    response = ''
    return normal, response

SPEC = Str({
    None: End(cmd_user_show),
    'help': End(cmd_user_help),
    'show': End(cmd_user_show),
    'attr': ArgsUser(End(cmd_user_attr)),
    'get': ArgsUser(ArgsString(End(cmd_user_get))),
    'set': ArgsUser(ArgsString(ArgsJson(End(cmd_user_set)))),
    'eyes': ArgsUser(Str({
        None: End(cmd_user_eyes_show),
        'show': End(cmd_user_eyes_show),
        'delete': ArgsInt(End(cmd_user_eyes_delete)),
    })),
    'add': ArgsJsonBoolean(ArgsJsonString(End(cmd_user_add))),
})
