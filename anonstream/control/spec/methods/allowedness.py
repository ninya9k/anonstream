# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from quart import current_app

from anonstream.control.exceptions import CommandFailed
from anonstream.control.spec.common import Str, End, ArgsStr, ArgsJsonBoolean, ArgsJsonString, ArgsJsonStringArray
from anonstream.control.spec.utils import json_dumps_contiguous

ALLOWEDNESS = current_app.allowedness

async def cmd_allowedness_help():
    normal = ['allowedness', 'help']
    response = (
        'Usage: allowedness [show | set default BOOLEAN | add LIST KEYTUPLE VALUE | remove LIST KEYTUPLE VALUE]\n'
        'Commands:\n'
        ' allowedness [show]........................\n'
        ' allowedness setdefault BOOLEAN............set the default allowedness\n'
        #' allowedness clear LIST all................\n'
        #' allowedness clear LIST keytuple KEYTUPLE..\n'
        ' allowedness add LIST KEYTUPLE STRING......add to the blacklist/whitelist\n'
        ' allowedness remove LIST KEYTUPLE STRING...remove from the blacklist/whitelist\n'
        'Definitions:\n'
        ' BOOLEAN...................................={true | false}\n'
        ' LIST......................................={blacklist | whitelist}\n'
        ' KEYTUPLE..................................keys to burrow into a user with, e.g. (\'tripcode\', \'digest\'), encoded as a json array\n'
        ' STRING....................................a json string\n'
    )
    return normal, response

async def cmd_allowedness_show():
    allowedness_for_json = {
        'blacklist': {},
        'whitelist': {},
        'default': ALLOWEDNESS['default'],
    }
    for colourlist in ('blacklist', 'whitelist'):
        for keytuple, values in ALLOWEDNESS[colourlist].items():
            allowedness_for_json[colourlist]['.'.join(keytuple)] = sorted(values)
    normal = ['allowedness', 'show']
    response = json.dumps(allowedness_for_json) + '\n'
    return normal, response

async def cmd_allowedness_setdefault(value):
    ALLOWEDNESS['default'] = value
    normal = ['allowednesss', 'setdefault', json_dumps_contiguous(value)]
    response = ''
    return normal, response

async def cmd_allowedness_add(colourlist, keytuple_list, value):
    keytuple = tuple(keytuple_list)
    try:
        values = ALLOWEDNESS[colourlist][keytuple]
    except KeyError:
        raise CommandFailed(f'no such keytuple {keytuple!r} in list {colourlist!r}')
    else:
        values.add(value)
    normal = [
        'allowednesss',
        'add',
        colourlist,
        json_dumps_contiguous(keytuple),
        json_dumps_contiguous(value),
    ]
    response = ''
    return normal, response

async def cmd_allowedness_remove(colourlist, keytuple_list, value):
    keytuple = tuple(keytuple_list)
    try:
        values = ALLOWEDNESS[colourlist][keytuple]
    except KeyError:
        raise CommandFailed(f'no such keytuple {keytuple!r} in list {colourlist!r}')
    else:
        try:
            values.remove(value)
        except KeyError:
            pass
    normal = [
        'allowednesss',
        'remove',
        colourlist,
        json_dumps_contiguous(keytuple),
        json_dumps_contiguous(value),
    ]
    response = ''
    return normal, response

SPEC = Str({
    None: End(cmd_allowedness_show),
    'help': End(cmd_allowedness_help),
    'show': End(cmd_allowedness_show),
    'setdefault': ArgsJsonBoolean(End(cmd_allowedness_setdefault)),
    #'clear': cmd_allowedness_clear,
    'add': ArgsStr({
        'blacklist': ArgsJsonStringArray(ArgsJsonString(End(cmd_allowedness_add))),
        'whitelist': ArgsJsonStringArray(ArgsJsonString(End(cmd_allowedness_add))),
    }),
    'remove': ArgsStr({
        'blacklist': ArgsJsonStringArray(ArgsJsonString(End(cmd_allowedness_remove))),
        'whitelist': ArgsJsonStringArray(ArgsJsonString(End(cmd_allowedness_remove))),
    }),
})
