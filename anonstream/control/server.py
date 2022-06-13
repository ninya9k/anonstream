import asyncio
import json

from anonstream.stream import get_stream_title, set_stream_title

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
                ' exit.......................close the connection\n'
                ' title [show]...............show the stream title\n'
                ' title set TITLE............set the stream title\n'
                ' user [show]................show a list of users\n'
                ' user set USER ATTR VALUE...set an attribute of a user\n'
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
                'Arguments:\n'
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

METHOD_HELP = 'help'
METHOD_EXIT = 'exit'
METHOD_TITLE = 'title'

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
}
