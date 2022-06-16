import json

from anonstream.control.exceptions import CommandFailed
from anonstream.control.spec import Spec, NoParse
from anonstream.control.spec.common import Str, End, ArgsJsonString
from anonstream.control.spec.utils import get_item, json_dumps_contiguous
from anonstream.stream import get_stream_title, set_stream_title

async def cmd_title_help():
    normal = ['title', 'help']
    response = (
        'Usage: title [show | set TITLE]\n'
        'Commands:\n'
        ' title [show].......show the stream title\n'
        ' title set TITLE....set the stream title to TITLE\n'
        'Definitions:\n'
        ' TITLE..............a json string, whitespace must be \\uXXXX-escaped\n'
    )
    return normal, response

async def cmd_title_show():
    normal = ['title', 'show']
    response = json.dumps(await get_stream_title()) + '\n'
    return normal, response

async def cmd_title_set(title):
    try:
        await set_stream_title(title)
    except OSError as e:
        raise CommandFailed(f'could not set title: {e}') from e
    normal = ['title', 'set', json_dumps_contiguous(title)]
    response = ''
    return normal, response

SPEC = Str({
    None: End(cmd_title_show),
    'help': End(cmd_title_help),
    'show': End(cmd_title_show),
    'set': ArgsJsonString(End(cmd_title_set)),
})
