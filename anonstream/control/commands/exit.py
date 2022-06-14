from anonstream.control.exceptions import Exit, Garbage

async def command_exit(args):
    match args:
        case []:
            raise Exit
        case [*garbage]:
            raise Garbage(garbage)

async def command_exit_help(args):
    match args:
        case []:
            normal_options = ['help']
            response = (
                'Usage: exit\n'
                'close the connection\n'
            )
        case [*garbage]:
            raise Garbage(garbage)
    return normal_options, response
