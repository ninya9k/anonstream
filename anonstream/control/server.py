import asyncio
import json

from quart import current_app

from anonstream.chat import delete_chat_messages
from anonstream.stream import get_stream_title, set_stream_title
from anonstream.utils.user import USER_WEBSOCKET_ATTRS

USERS_BY_TOKEN = current_app.users_by_token
USERS = current_app.users
USERS_UPDATE_BUFFER = current_app.users_update_buffer

class UnknownMethod(Exception):
    pass

class UnknownCommand(Exception):
    pass

class UnknownArgument(Exception):
    pass

class BadArgument(Exception):
    pass

class Incomplete(Exception):
    pass

class Garbage(Exception):
    pass

class Failed(Exception):
    pass

class Exit(Exception):
    pass

def start_control_server_at(address):
    return asyncio.start_unix_server(serve_control_client, address)

async def serve_control_client(reader, writer):
    while line := await reader.readline():
        try:
            request = line.decode('utf-8')
        except UnicodeDecodeError as e:
            normal, response = None, str(e)
        else:
            try:
                normal, response = await parse_request(request)
            except Exit:
                writer.close()
                break

        if normal is not None:
            normal_method, normal_options = normal
            if normal_method is not None:
                writer.write(normal_method.encode())
                for arg in normal_options:
                    writer.write(b' ')
                    writer.write(arg.encode())
                writer.write(b'\n')
        elif response:
            writer.write(b'error: ')

        writer.write(response.encode())
        await writer.drain()

async def parse_request(request):
    try:
        method, *options = request.split()
    except ValueError:
        normal, response = (None, []), ''
    else:
        try:
            normal, response = await parse(method, options)
        except UnknownMethod as e:
            unknown_method, *_ = e.args
            normal = None
            response = f"method {unknown_method!r} is unknown, try 'help'\n"
        except UnknownCommand as e:
            method, unknown_command, *_ = e.args
            normal = None
            response = f"command {unknown_command!r} is unknown, try {f'{method} help'!r}\n"
        except BadArgument as e:
            reason, *_ = e.args
            normal = None
            response = f"{reason}, try {f'{method} help'!r}\n"
        except Incomplete as e:
            method, *_ = e.args
            normal = None
            response = f"command is incomplete, try {f'{method} help'!r}\n"
        except Garbage as e:
            garbage, *_ = e.args
            normal = None
            response = f"command has trailing garbage {garbage!r}, try {f'{method} help'!r}\n"
        except Failed as e:
            reason, *_ = e.args
            normal = None
            response = reason + '\n'
    return normal, response

async def parse(method, options):
    try:
        command, *args = options
    except ValueError:
        command, args = None, []
    try:
        functions = METHOD_COMMAND_FUNCTIONS[method]
    except KeyError:
        raise UnknownMethod(method)
    else:
        normal_method = method
        try:
            fn = functions[command]
        except KeyError:
            raise UnknownCommand(method, command)
        else:
            try:
                normal_options, response = await fn(args)
            except Incomplete as e:
                raise Incomplete(method) from e
    normal = (normal_method, normal_options)
    return normal, response

async def command_help(args):
    match args:
        case []:
            normal_options = []
            response = (
                'Usage: METHOD [COMMAND | help]\n'
                'Examples:\n'
                ' help.......................show this help message\n'
                ' exit.......................close the control connection\n'
                ' title [show]...............show the stream title\n'
                ' title set TITLE............set the stream title\n'
                ' user [show]................show a list of users\n'
                ' user set USER ATTR VALUE...set an attribute of a user\n'
                ' user show USERS............show a list of users\n'
                ' user kick USERS [FAREWELL].kick users\n'
                ' user eyes USER [show]......show a list of active video responses\n'
                ' user eyes USER blind IDS...kill a set of video responses\n'
                ' chat show MESSAGES.........show a list of messages\n'
                ' chat delete MESSAGES.......delete a set of messages\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_help_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                'Usage: help\n'
                'show usage syntax and examples\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_exit(args):
    match args:
        case []:
            raise Exit
        case [*garbage]:
            raise Garbage(garbage)

async def command_exit_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                'Usage: exit\n'
                'close the connection\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_title_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                'Usage: title [show | set TITLE]\n'
                'Commands:\n'
                ' title [show].......show the stream title\n'
                ' title set TITLE....set the stream title to TITLE\n'
                'Definitions:\n'
                ' TITLE..............a json-encoded string, whitespace must be \\uXXXX-escaped\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_title_show(args):
    match args:
        case []:
            normal_options = ['show']
            response = json.dumps(await get_stream_title()) + '\n' 
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_title_set(args):
    match args:
        case [title_json]:
            try:
                title = json.loads(title_json)
            except json.JSONDecodeError as e:
                raise BadArgument('could not decode json')
            else:
                if not isinstance(title, str):
                    raise BadArgument('could not decode json as string')
                else:
                    try:
                        await set_stream_title(title)
                    except OSError as e:
                        raise Failed(str(e)) from e
                    normal_options = ['set', json.dumps(title).replace(' ', r'\u0020')]
                    response = ''
        case []:
            raise Incomplete
        case [_, *garbage]:
            raise Garbage(garbage)
    return normal_options, response

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
            normal_options = ['attr', 'token', json.dumps(token).replace(' ', r'\u0020')]
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
                raise Failed(f"user has no attribute {attr!r}, try 'user attr token {token}'")
            try:
                value_json = json.dumps(value)
            except TypeError:
                raise Failed(f'attribute {attr!r} is not JSON serializable')
            normal_options = ['get', 'token', json.dumps(token).replace(' ', r'\u0020'), attr]
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
                raise Failed(f"user has no attribute {attr!r}, try 'user attr token {TOKEN}")
            try:
                value = json.loads(value_json)
            except JSON.JSONDecodeError:
                raise Failed('could not decode json')
            user[attr] = value
            if attr in USER_WEBSOCKET_ATTRS:
                USERS_UPDATE_BUFFER.add(token)
            normal_options = ['set', 'token', json.dumps(token).replace(' ', r'\u0020'), attr, json.dumps(value)]
            response = ''
        case []:
            raise Incomplete
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_chat_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                'Usage: chat {show [MESSAGES] | delete SEQS}\n'
                'Commands:\n'
                ' chat show [MESSAGES]......show chat messages\n'
                ' chat delete SEQS..........delete chat messages\n'
                'Definitions:\n'
                ' MESSAGES..................undefined\n'
                ' SEQS......................=SEQ [SEQ...]\n'
                ' SEQ.......................a chat message\'s seq, base-10 integer\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_chat_delete(args):
    match args:
        case []:
            raise Incomplete
        case _:
            try:
                seqs = list(map(int, args))
            except ValueError as e:
                raise BadArgument('SEQ must be a base-10 integer') from e
            delete_chat_messages(seqs)
            normal_options = ['delete', *map(str, seqs)]
            response = ''
    return normal_options, response

METHOD_HELP = 'help'
METHOD_EXIT = 'exit'
METHOD_TITLE = 'title'
METHOD_CHAT = 'chat'
METHOD_USER = 'user'

METHOD_COMMAND_FUNCTIONS = {
    METHOD_HELP: {
        None: command_help,
        'help': command_help_help,
    },
    METHOD_EXIT: {
        None: command_exit,
        'help': command_exit_help,
    },
    METHOD_TITLE: {
        None: command_title_show,
        'help': command_title_help,
        'show': command_title_show,
        'set': command_title_set,
    },
    METHOD_CHAT: {
        None: command_chat_help,
        'help': command_chat_help,
        'delete': command_chat_delete,
    },
    METHOD_USER: {
        None: command_user_show,
        'help': command_user_help,
        'show': command_user_show,
        'attr': command_user_attr,
        'get': command_user_get,
        'set': command_user_set,
    },
}
