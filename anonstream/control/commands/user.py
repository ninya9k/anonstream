import json

from quart import current_app

from anonstream.control.exceptions import BadArgument, Incomplete, Garbage, Failed
from anonstream.control.utils import json_dumps_contiguous
from anonstream.utils.user import USER_WEBSOCKET_ATTRS

USERS_BY_TOKEN = current_app.users_by_token
USERS = current_app.users
USERS_UPDATE_BUFFER = current_app.users_update_buffer

async def command_user_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                    'Usage: user [show | attr USER | get USER ATTR | set USER ATTR VALUE]\n'
                    'Commands:\n'
                    ' user [show]...........show all users\' tokens\n'
                    ' user attr USER........show names of a user\'s attributes\n'
                    ' user get USER ATTR....show an attribute of a user\n'
                    ' user set USER ATTR....set an attribute of a user\n'
                    'Definitions:\n'
                    ' USER..................={token TOKEN | hash HASH}\n'
                    ' TOKEN.................a token\n'
                    ' HASH..................a token hash\n'
                    ' ATTR..................a user attribute, re:[a-z0-9_]+\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_user_show(args):
    match args:
        case []:
            normal_options = ['show']
            response = json.dumps(tuple(USERS_BY_TOKEN)) + '\n'
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_user_attr(args):
    match args:
        case []:
            raise Incomplete
        case ['token', token_json]:
            try:
                token = json.loads(token_json)
            except json.JSONDecodeError:
                raise BadArgument('could not decode token as json')
            try:
                user = USERS_BY_TOKEN[token]
            except KeyError:
                raise Failed(f"no user exists with token {token!r}, try 'user show'")
            normal_options = ['attr', 'token', json_dumps_contiguous(token)]
            response = json.dumps(tuple(user.keys())) + '\n'
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_user_get(args):
    match args:
        case ['token', token_json, attr]:
            try:
                token = json.loads(token_json)
            except json.JSONDecodeError:
                raise BadArgument('could not decode token as json')
            try:
                user = USERS_BY_TOKEN[token]
            except KeyError:
                raise Failed(f"no user exists with token {token!r}, try 'user show'")
            try:
                value = user[attr]
            except KeyError:
                raise Failed(f"user has no attribute {attr!r}, try 'user attr token {json_dumps_contiguous(token)}'")
            try:
                value_json = json.dumps(value)
            except TypeError:
                raise Failed(f'attribute {attr!r} is not JSON serializable')
            normal_options = ['get', 'token', json_dumps_contiguous(token), attr]
            response = value_json + '\n'
        case []:
            raise Incomplete
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_user_set(args):
    match args:
        case ['token', token_json, attr, value_json]:
            try:
                token = json.loads(token_json)
            except json.JSONDecodeError:
                raise BadArgument('could not decode token as json')
            try:
                user = USERS_BY_TOKEN[token]
            except KeyError:
                raise Failed(f"no user exists with token {token!r}, try 'user show'")
            try:
                value = user[attr]
            except KeyError:
                raise Failed(f"user has no attribute {attr!r}, try 'user attr token {json_dumps_contiguous(token)}")
            try:
                value = json.loads(value_json)
            except json.JSONDecodeError:
                raise Failed('could not decode json')
            user[attr] = value
            if attr in USER_WEBSOCKET_ATTRS:
                USERS_UPDATE_BUFFER.add(token)
            normal_options = ['set', 'token', json_dumps_contiguous(token), attr, json_dumps_contiguous(value)]
            response = ''
        case []:
            raise Incomplete
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response
