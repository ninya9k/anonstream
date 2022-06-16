# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

def get_item(index, words):
    try:
        word = words[index]
    except IndexError:
        word = None
    else:
        if not word:
            raise NoParse(f'empty word at position {index}')
    return word

def json_dumps_contiguous(obj, **kwargs):
    return json.dumps(obj, **kwargs).replace(' ', r'\u0020')

def startswith(string, prefix):
    if string is None or prefix is None:
        return string is prefix
    return string.startswith(prefix)
