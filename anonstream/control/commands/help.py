from anonstream.control.exceptions import Garbage

async def command_help(args):
    match args:
        case []:
            normal_options = []
            response = (
                'Usage: METHOD [COMMAND | help]\n'
                'Examples:\n'
                ' help.......................show this help message\n'
                ' exit.......................close the control connection\n'
                ' title [show]...............show the stream title\n'
                ' title set TITLE............set the stream title\n'
                ' user [show]................show a list of users\n'
                ' user attr USER.............set an attribute of a user\n'
                ' user get USER ATTR.........set an attribute of a user\n'
                ' user set USER ATTR VALUE...set an attribute of a user\n'
                #' user kick USERS [FAREWELL].kick users\n'
                #' user eyes USER [show]......show a list of active video responses\n'
                #' user eyes USER delete IDS..kill a set of video responses\n'
                #' chat show MESSAGES.........show a list of messages\n'
                ' chat delete SEQS...........delete a set of messages\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response

async def command_help_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                'Usage: help\n'
                'show usage syntax and examples\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response
