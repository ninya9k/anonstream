import json
import re

import aiofiles
from quart import escape

class BadEmote(Exception):
    pass

class BadEmoteName(BadEmote):
    pass

def _load_emote_schema(emotes):
    for key in ('name', 'file', 'width', 'height'):
        for emote in emotes:
            if key not in emote:
                raise BadEmote(f'emotes must have a `{key}`: {emote}')
    precompute_emote_regex(emotes)
    return emotes

def load_emote_schema(filepath):
    with open(filepath) as fp:
        emotes = json.load(fp)
    return _load_emote_schema(emotes)

async def load_emote_schema_async(filepath):
    async with aiofiles.open(filepath) as fp:
        data = await fp.read(8192)
    return _load_emote_schema(json.loads(data))

def precompute_emote_regex(schema):
    for emote in schema:
        if not emote['name']:
            raise BadEmoteName(f'emote names cannot be empty: {emote}')
        if re.search(r'\s', emote['name']):
            raise BadEmoteName(
                f'whitespace is not allowed in emote names: {emote["name"]!r}'
            )
        for length in (emote['width'], emote['height']):
            if length is not None and (not isinstance(length, int) or length < 0):
                raise BadEmoteName(
                    f'emote dimensions must be null or non-negative integers: '
                    f'{emote}'
                )
        # If the emote name begins with a word character [a-zA-Z0-9_],
        # match only if preceded by a non-word character or the empty
        # string.  Similarly for the end of the emote name.
        # Examples:
        #  * ":joy:" matches "abc :joy:~xyz"   and   "abc:joy:xyz"
        #  * "JoySi" matches "abc JoySi~xyz" but NOT "abcJoySiabc"
        onset = r'(?:^|(?<=\W))' if re.fullmatch(r'\w', emote['name'][0]) else r''
        finish = r'(?:$|(?=\W))' if re.fullmatch(r'\w', emote['name'][-1]) else r''
        emote['regex'] = re.compile(''.join(
            (onset, re.escape(escape(emote['name'])), finish)
        ))
