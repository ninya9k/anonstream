# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from quart import current_app

from anonstream.control.exceptions import CommandFailed
from anonstream.control.spec.common import Str, End, ArgsJsonString
from anonstream.control.spec.utils import json_dumps_contiguous
from anonstream.helpers.tripcode import generate_tripcode

CONFIG = current_app.config

async def cmd_tripcode_help():
    normal = ['tripcode', 'help']
    response = (
        'Usage: tripcode generate PASSWORD\n'
        'Commands:\n'
        ' tripcode generate PASSWORD....show tripcode for given password\n'
        'Definitions:\n'
        ' PASSWORD................json string, max length in config.toml (`chat.max_tripcode_password_length`)\n'
    )
    return normal, response

async def cmd_tripcode_generate(password):
    if len(password) > CONFIG['CHAT_TRIPCODE_PASSWORD_MAX_LENGTH']:
        raise CommandFailed(
            f'password exceeded maximum configured length of '
            f'{CONFIG["CHAT_TRIPCODE_PASSWORD_MAX_LENGTH"]} '
            f'characters'
        )
    tripcode = generate_tripcode(password)
    normal = ['tripcode', 'generate', json_dumps_contiguous(password)]
    response = json.dumps(tripcode) + '\n'
    return normal, response

SPEC = Str({
    None: End(cmd_tripcode_help),
    'help': End(cmd_tripcode_help),
    'generate': ArgsJsonString(End(cmd_tripcode_generate)),
})
