from anonstream.control.spec.common import Str, End

async def cmd_help():
    normal = ['help']
    response = (
        'Usage: METHOD [COMMAND | help]\n'
        'Examples:\n'
        ' help...........................show this help message\n'
        ' exit...........................close the control connection\n'
        ' title [show]...................show the stream title\n'
        ' title set TITLE................set the stream title\n'
        ' user [show]....................show a list of users\n'
        ' user attr USER.................set an attribute of a user\n'
        ' user get USER ATTR.............set an attribute of a user\n'
        ' user set USER ATTR VALUE.......set an attribute of a user\n'
        #' user kick USERS [FAREWELL].....kick users\n'
        ' user eyes USER [show]..........show a list of active video responses\n'
        ' user eyes USER delete EYES_ID..end a video response\n'
        #' chat show MESSAGES.............show a list of messages\n'
        ' chat delete SEQS...............delete a set of messages\n'
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
