# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import itertools
import json

from quart import current_app

from anonstream.chat import delete_chat_messages
from anonstream.control.exceptions import CommandFailed
from anonstream.control.spec import NoParse
from anonstream.control.spec.common import Str, End, Args, ArgsJsonString, ArgsUser
from anonstream.control.spec.utils import get_item, json_dumps_contiguous
from anonstream.chat import add_chat_message, Rejected

MESSAGES = current_app.messages

class ArgsSeqs(Args):
    def consume(self, words, index):
        seqs = []
        for i in itertools.count():
            seq_string = get_item(index + i, words)
            try:
                seq = int(seq_string)
            except TypeError as e:
                if not seqs:
                    raise NoParse('incomplete: expected SEQ') from e
                else:
                    break
            except ValueError as e:
                raise NoParse(
                        'could not decode {word!r} as base-10 integer'
                ) from e
            else:
                seqs.append(seq)
        return self.spec, i + 1, seqs

async def cmd_chat_help():
    normal = ['chat', 'help']
    response = (
        'Usage: chat {show | delete SEQS | add USER NONCE COMMENT}\n'
        'Commands:\n'
        ' chat show......................show all chat messages\n'
        ' chat delete SEQS...............delete chat messages\n'
        ' chat add USER NONCE COMMENT....add chat message\n'
        'Definitions:\n'
        ' SEQS.......................=SEQ [SEQ...]\n'
        ' SEQ........................a chat message\'s seq, base-10 integer\n'
        ' USER.......................={token TOKEN | hash HASH}\n'
        ' TOKEN......................a user\'s token, json string\n'
        ' HASH.......................a user\'s token hash\n'
        ' NONCE......................a chat message\'s nonce, json string\n'
        ' COMMENT....................json string\n'
    )
    return normal, response

async def cmd_chat_show():
    normal = ['chat', 'show']
    response = json.dumps(tuple(MESSAGES), separators=(',', ':')) + '\n'
    return normal, response

async def cmd_chat_delete(*seqs):
    delete_chat_messages(seqs)
    normal = ['chat', 'delete', *map(str, seqs)]
    response = ''
    return normal, response

async def cmd_chat_add(user, nonce, comment):
    try:
        seq = add_chat_message(user, nonce, comment)
    except Rejected as e:
        raise CommandFailed(f'rejected: {e}') from e
    else:
        assert seq is not None
    normal = [
        'chat', 'add',
        'token', json_dumps_contiguous(user['token']),
        json_dumps_contiguous(nonce), json_dumps_contiguous(comment),
    ]
    response = str(seq) + '\n'
    return normal, response

SPEC = Str({
    None: End(cmd_chat_help),
    'help': End(cmd_chat_help),
    'show': End(cmd_chat_show),
    'delete': ArgsSeqs(End(cmd_chat_delete)),
    'add': ArgsUser(ArgsJsonString(ArgsJsonString(End(cmd_chat_add)))),
})
