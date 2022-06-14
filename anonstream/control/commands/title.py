import json

from anonstream.control.exceptions import BadArgument, Incomplete, Garbage, Failed
from anonstream.control.utils import json_dumps_contiguous
from anonstream.stream import get_stream_title, set_stream_title

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
                    normal_options = ['set', json_dumps_contiguous(title)]
                    response = ''
        case []:
            raise Incomplete
        case [_, *garbage]:
            raise Garbage(garbage)
    return normal_options, response
