from anonstream.control.spec.common import Str, End
from anonstream.control.exceptions import ControlSocketExit

async def cmd_exit():
    raise ControlSocketExit

async def cmd_exit_help():
    normal = ['exit', 'help']
    response = (
        'Usage: exit\n'
        'close the connection\n'
    )
    return normal, response

SPEC = Str({
    None: End(cmd_exit),
    'help': End(cmd_exit_help),
})
