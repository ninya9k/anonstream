from anonstream.control.commands.help import *
from anonstream.control.commands.exit import *
from anonstream.control.commands.title import *
from anonstream.control.commands.chat import *
from anonstream.control.commands.user import *

METHOD_HELP = 'help'
METHOD_EXIT = 'exit'
METHOD_TITLE = 'title'
METHOD_CHAT = 'chat'
METHOD_USER = 'user'

METHOD_COMMAND_FUNCTIONS = {
    METHOD_HELP: {
        None: command_help,
        'help': command_help_help,
    },
    METHOD_EXIT: {
        None: command_exit,
        'help': command_exit_help,
    },
    METHOD_TITLE: {
        None: command_title_show,
        'help': command_title_help,
        'show': command_title_show,
        'set': command_title_set,
    },
    METHOD_CHAT: {
        None: command_chat_help,
        'help': command_chat_help,
        'delete': command_chat_delete,
    },
    METHOD_USER: {
        None: command_user_show,
        'help': command_user_help,
        'show': command_user_show,
        'attr': command_user_attr,
        'get': command_user_get,
        'set': command_user_set,
        'eyes': command_user_eyes,
    },
}


