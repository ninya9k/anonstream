import asyncio
import json

from anonstream.stream import get_stream_title

def start_control_server_at(address):
    return asyncio.start_unix_server(
        handle_control_client,
        address,
    )

async def handle_control_client(reader, writer):
    while line := await reader.readline():
        try:
            request = line.decode('utf-8')
        except UnicodeDecodeError as e:
            response = f'error: {e}'
        else:
            method, args, normal, response = await parse(request)
            if method is None:
                pass
            elif normal is not None:
                writer.write(f'{normal}\n'.encode())
            elif response is not None:
                writer.write(f'error: '.encode())
        if response is not None:
            writer.write(response.encode())
            await writer.drain()
        else:
            writer.close()
            break

async def parse(request):
    try:
        method, *args = request.split()
    except ValueError:
        method, args, normal, response = None, [], None, ''
    else:
        match method:
            case 'help':
                normal_args, response = await parse_help(args)
            case 'exit':
                normal_args, response = await parse_exit(args)
            case 'title':
                normal_args, response = await parse_title(args)
            case _:
                normal_args = None
                response = f"method {method!r} is unknown, try 'help'\n"
        if normal_args is None:
            normal = None
            if response is None:
                response = f"command {args[0]!r} is unknown, try {f'{method} help'!r}\n"
        elif len(normal_args) == 0:
            normal = method
        else:
            normal = f'{method} {" ".join(normal_args)}' or method
    return method, args, normal, response

async def parse_help(args):
    match args:
        case []:
            normal_args = []
            response = (
                'Usage: METHOD {COMMAND | help}\n'
                'Examples:\n'
                ' help.......................show this help message\n'
                ' exit.......................close the connection\n'
                ' title [show [CODEC]].......show the stream title\n'
                ' title set TITLE............set the stream title\n'
                ' user [show]................show a list of users\n'
                ' user set USER ATTR VALUE...set an attribute of a user\n'
            )
        case ['help']:
            normal_args = ['help']
            response = (
                'Usage: help\n'
                'show usage syntax and examples\n'
            )
        case _:
            normal_args = None
            response = None
    return normal_args, response

async def parse_exit(args):
    match args:
        case []:
            normal_args = []
            response = None
        case ['help']:
            normal_args = ['help']
            response = (
                'Usage: {exit | quit}\n'
                'close the connection\n'
            )
        case _:
            normal_args = None
            response = None
    return normal_args, response

async def parse_title(args):
    match args:
        case [] | ['show'] | ['show', 'json']:
            normal_args = ['show', 'json']
            response = json.dumps(await get_stream_title()) + '\n'
        case ['show', 'utf-8']:
            normal_args = ['show']
            response = await get_stream_title() + '\n'
        case ['show', arg, *_]:
            normal_args = None
            response = f"option {arg!r} is unknown, try 'title help'\n"
        case ['help']:
            normal_args = ['help']
            response = (
                'Usage: title {show [CODEC] | set TITLE}\n'
                'Commands:\n'
                ' title show [CODEC].....show the stream title\n'
                ' title set TITLE........set the stream title to TITLE collapsing whitespace\n'
                'Arguments:\n'
                ' CODEC..................=[utf-8 | json]\n'
                ' TITLE..................a UTF-8-encoded string\n'
            )
        case _:
            normal_args = None
            response = None
    return normal_args, response
