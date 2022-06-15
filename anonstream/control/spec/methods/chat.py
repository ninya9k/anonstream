import itertools

from anonstream.chat import delete_chat_messages
from anonstream.control.spec import NoParse
from anonstream.control.spec.common import Str, End, Args
from anonstream.control.spec.utils import get_item, json_dumps_contiguous

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
        'Usage: chat {show [MESSAGES] | delete SEQS}\n'
        'Commands:\n'
        #' chat show [MESSAGES]......show chat messages\n'
        ' chat delete SEQS..........delete chat messages\n'
        'Definitions:\n'
        #' MESSAGES..................undefined\n'
        ' SEQS......................=SEQ [SEQ...]\n'
        ' SEQ.......................a chat message\'s seq, base-10 integer\n'
    )
    return normal, response

async def cmd_chat_delete(*seqs):
    delete_chat_messages(seqs)
    normal = ['chat', 'delete', *map(str, seqs)]
    response = ''
    return normal, response

SPEC = Str({
    None: End(cmd_chat_help),
    'help': End(cmd_chat_help),
    'delete': ArgsSeqs(End(cmd_chat_delete)),
})
