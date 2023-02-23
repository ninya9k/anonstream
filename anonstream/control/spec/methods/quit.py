# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

from anonstream.control.spec.common import Str, End
from anonstream.control.exceptions import ControlSocketExit

async def cmd_quit():
    raise ControlSocketExit

async def cmd_quit_help():
    normal = ['quit', 'help']
    response = (
        'Usage: quit\n'
        'Commands:\n'
        ' quit......close the connection\n'
    )
    return normal, response

SPEC = Str({
    None: End(cmd_quit),
    'help': End(cmd_quit_help),
})
