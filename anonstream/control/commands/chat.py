from anonstream.control.exceptions import BadArgument, Incomplete, Garbage
from anonstream.chat import delete_chat_messages

async def command_chat_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                'Usage: chat {show [MESSAGES] | delete SEQS}\n'
                'Commands:\n'
                ' chat show [MESSAGES]......show chat messages\n'
                ' chat delete SEQS..........delete chat messages\n'
                'Definitions:\n'
                ' MESSAGES..................undefined\n'
                ' SEQS......................=SEQ [SEQ...]\n'
                ' SEQ.......................a chat message\'s seq, base-10 integer\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_chat_delete(args):
    match args:
        case []:
            raise Incomplete
        case _:
            try:
                seqs = list(map(int, args))
            except ValueError as e:
                raise BadArgument('SEQ must be a base-10 integer') from e
            delete_chat_messages(seqs)
            normal_options = ['delete', *map(str, seqs)]
            response = ''
    return normal_options, response
