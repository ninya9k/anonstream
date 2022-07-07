# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

from anonstream.control.spec import ParseException, Parsed
from anonstream.control.spec.common import Str
from anonstream.control.spec.methods.allowedness import SPEC as SPEC_ALLOWEDNESS
from anonstream.control.spec.methods.chat import SPEC as SPEC_CHAT
from anonstream.control.spec.methods.exit import SPEC as SPEC_EXIT
from anonstream.control.spec.methods.help import SPEC as SPEC_HELP
from anonstream.control.spec.methods.title import SPEC as SPEC_TITLE
from anonstream.control.spec.methods.user import SPEC as SPEC_USER

SPEC = Str({
    'help': SPEC_HELP,
    'exit': SPEC_EXIT,
    'title': SPEC_TITLE,
    'chat': SPEC_CHAT,
    'user': SPEC_USER,
    'allowednesss': SPEC_ALLOWEDNESS,
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
