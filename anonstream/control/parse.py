# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

from anonstream.control.spec import ParseException, Parsed
from anonstream.control.spec.common import Str
from anonstream.control.spec.methods.allowedness import SPEC as SPEC_ALLOWEDNESS
from anonstream.control.spec.methods.chat import SPEC as SPEC_CHAT
from anonstream.control.spec.methods.config import SPEC as SPEC_CONFIG
from anonstream.control.spec.methods.emote import SPEC as SPEC_EMOTE
from anonstream.control.spec.methods.help import SPEC as SPEC_HELP
from anonstream.control.spec.methods.quit import SPEC as SPEC_QUIT
from anonstream.control.spec.methods.title import SPEC as SPEC_TITLE
from anonstream.control.spec.methods.tripcode import SPEC as SPEC_TRIPCODE
from anonstream.control.spec.methods.user import SPEC as SPEC_USER

SPEC = Str({
    'help': SPEC_HELP,
    'quit': SPEC_QUIT,
    'title': SPEC_TITLE,
    'chat': SPEC_CHAT,
    'user': SPEC_USER,
    'allowednesss': SPEC_ALLOWEDNESS,
    'emote': SPEC_EMOTE,
    'config': SPEC_CONFIG,
    'tripcode': SPEC_TRIPCODE,
})

async def parse(request):
    words = request.split()
    if not words:
        normal, response = None, ''
    else:
        spec = SPEC
        index = 0
        args = []
        while True:
            try:
                spec, n_consumed, more_args = spec.consume(words, index)
            except ParseException as e:
                normal, response = None, e.args[0] + '\n'
                break
            except Parsed as e:
                fn, *_ = e.args
                normal, response = await fn(*args)
                break
            else:
                index += n_consumed
                args.extend(more_args)
    return normal, response
