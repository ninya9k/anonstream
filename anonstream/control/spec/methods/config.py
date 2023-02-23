# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from quart import current_app

from anonstream.control.exceptions import CommandFailed
from anonstream.control.spec.common import Str, End, ArgsString

CONFIG = current_app.config

async def cmd_config_help():
    normal = ['config', 'help']
    response = (
        'Usage: config show OPTION\n'
        'Commands:\n'
        ' config show OPTION....show entry in app.config\n'
        'Definitions:\n'
        ' OPTION................app.config key, re:[A-Z0-9_]+\n'
    )
    return normal, response

async def cmd_config_show(option):
    if option in {'SECRET_KEY', 'SECRET_KEY_STRING'}:
        raise CommandFailed('not going to show our secret key')
    try:
        value = CONFIG[option]
    except KeyError:
        raise CommandFailed(f'no config option with key {option!r}')
    try:
        value_json = json.dumps(value)
    except (TypeError, ValueError):
        raise CommandFailed(f'value is not json serializable')
    normal = ['config', 'show']
    response = value_json + '\n'
    return normal, response

SPEC = Str({
    None: End(cmd_config_help),
    'help': End(cmd_config_help),
    'show': ArgsString(End(cmd_config_show)),
})
