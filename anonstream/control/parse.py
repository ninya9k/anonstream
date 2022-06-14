import json

from anonstream.control.exceptions import UnknownMethod, UnknownCommand, BadArgument, Incomplete, Garbage, Failed
from anonstream.control.commands import METHOD_COMMAND_FUNCTIONS

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
