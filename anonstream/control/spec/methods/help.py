# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

from anonstream.control.spec.common import Str, End

async def cmd_help():
    normal = ['help']
    response = (
        'Usage: METHOD [COMMAND | help]\n'
        'Examples:\n'
        ' help...........................show this help message\n'
        ' quit...........................close the control connection\n'
        ' title [show]...................show the stream title\n'
        ' title set TITLE................set the stream title\n'
        ' user [show]....................show a list of users\n'
        ' user attr USER.................set an attribute of a user\n'
        ' user get USER ATTR.............set an attribute of a user\n'
        ' user set USER ATTR VALUE.......set an attribute of a user\n'
        ' user eyes USER [show]..........show a list of active video responses\n'
        ' user eyes USER delete EYES_ID..end a video response\n'
        #' chat show MESSAGES.............show a list of messages\n'
        ' chat delete SEQS...............delete a set of messages\n'
        ' allowedness [show].............show the current allowedness\n'
        ' allowedness setdefault BOOLEAN.set the default allowedness\n'
        ' allowedness add SET STRING.....add to the blacklist/whitelist\n'
        ' allowedness remove SET STRING..remove from the blacklist/whitelist\n'
        ' emote reload...................try reloading the emote schema\n'
    )
    return normal, response

async def cmd_help_help():
    normal = ['help', 'help']
    response = (
        'Usage: help\n'
        'show usage syntax and examples\n'
    )
    return normal, response

SPEC = Str({
    None: End(cmd_help),
    'help': End(cmd_help_help),
})
