# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from quart import current_app

from anonstream.emote import load_emote_schema_async, BadEmote
from anonstream.helpers.emote import get_emote_markup
from anonstream.control.spec.common import Str, End
from anonstream.control.exceptions import CommandFailed

CONFIG = current_app.config
EMOTES = current_app.emotes

async def cmd_emote_help():
    normal = ['emote', 'help']
    response = (
        'Usage: emote {show | reload}\n'
        'Commands:\n'
        ' emote show........show all current emotes\n'
        ' emote reload......try to reload the emote schema (existing messages are not modified)\n'
    )
    return normal, response

async def cmd_emote_show():
    emotes_for_json = [emote.copy() for emote in EMOTES]
    for emote in emotes_for_json:
        emote['regex'] = emote['regex'].pattern
    normal = ['emote', 'show']
    response = json.dumps(emotes_for_json) + '\n'
    return normal, response

async def cmd_emote_reload():
    try:
        emotes = await load_emote_schema_async(CONFIG['EMOTE_SCHEMA'])
    except OSError as e:
        raise CommandFailed(f'could not read emote schema: {e}') from e
    except json.JSONDecodeError as e:
        raise CommandFailed('could not decode emote schema as json') from e
    except BadEmote as e:
        error, *_ = e.args
        raise CommandFailed(error) from e
    else:
        # Mutate current_app.emotes in place
        EMOTES.clear()
        for emote in emotes:
            EMOTES.append(emote)
        # Clear emote markup cache -- emotes by the same name may have changed
        get_emote_markup.cache_clear()
    normal = ['emote', 'reload']
    response = ''
    return normal, response

SPEC = Str({
    None: End(cmd_emote_help),
    'help': End(cmd_emote_help),
    'show': End(cmd_emote_show),
    'reload': End(cmd_emote_reload),
})

