# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

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
