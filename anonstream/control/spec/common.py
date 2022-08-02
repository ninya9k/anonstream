# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from quart import current_app

from anonstream.control.spec import Spec, NoParse, Ambiguous, BadArgument, Parsed
from anonstream.control.spec.utils import get_item, startswith

USERS_BY_TOKEN = current_app.users_by_token
USERS = current_app.users

class Str(Spec):
    AS_ARG = False

    def __init__(self, directives):
        self.directives = directives

    def consume(self, words, index):
        word = get_item(index, words)
        candidates = tuple(filter(
            lambda directive: startswith(directive, word),
            self.directives,
        ))
        try:
            directive = candidates[0]
        except IndexError as e:
            if word is None:
                reason = f'incomplete: expected one of {set(self.directives)}'
            else:
                reason = (
                    f'bad word at position {index} {word!r}: '
                    f'expected one of {set(self.directives)}'
                )
            raise NoParse(reason) from e
        else:
            if len(candidates) > 1:
                raise Ambiguous(
                    f'bad word at position {index} {word!r}: ambiguous '
                    f'abbreviation: {set(candidates)}'
                )
        args = []
        if self.AS_ARG:
            args.append(directive)
        return self.directives[directive], 1, args

class End(Spec):
    def __init__(self, fn):
        self.fn = fn

    def consume(self, words, index):
        if len(words) <= index:
            raise Parsed(self.fn)
        raise NoParse(f'garbage at position {index} {words[index:]!r}')

class Args(Spec):
    def __init__(self, spec):
        self.spec = spec

class ArgsStr(Str):
    AS_ARG = True

class ArgsInt(Args):
    def consume(self, words, index):
        try:
            n_string = words[index]
        except IndexError:
            raise NoParse(f'incomplete: expected integer')
        else:
            try:
                n = int(n_string)
            except ValueError:
                raise NoParse(
                    f'bad argument at position {index} {n_string!r}: '
                    f'could not decode base-10 integer'
                )
        return self.spec, 1, [n]

class ArgsString(Args):
    def transform_string(self, string):
        return string

    def consume(self, words, index):
        try:
            string = words[index]
        except IndexError:
            raise NoParse(f'incomplete: expected string')
        else:
            string = self.transform_string(string)
        return self.spec, 1, [string]

class ArgsJson(Args):
    def assert_obj(self, index, obj_json, obj):
        pass

    def transform_obj(self, obj):
        return obj

    def consume(self, words, index):
        try:
            obj_json = words[index]
        except IndexError:
            raise NoParse(f'incomplete: expected json')
        else:
            try:
               obj = json.loads(obj_json)
            except json.JSONDecodeError as e:
                raise NoParse(
                    f'bad argument at position {index} {obj_json!r}: '
                    f'could not decode json'
                )
            else:
                self.assert_obj(index, obj_json, obj)
                obj = self.transform_obj(obj)
        return self.spec, 1, [obj]

class ArgsJsonBoolean(ArgsJson):
    def assert_obj(self, index, obj_json, obj):
        if not isinstance(obj, bool):
            raise NoParse(
                    f'bad argument at position {index} {obj_json!r}: '
                    f'could not decode json boolean'
                )

class ArgsJsonString(ArgsJson):
    def assert_obj(self, index, obj_json, obj):
        if not isinstance(obj, str):
            raise NoParse(
                f'bad argument at position {index} {obj_json!r}: '
                f'could not decode json string'
            )

class ArgsJsonArray(ArgsJson):
    def assert_obj(self, index, obj_json, obj):
        if not isinstance(obj, list):
            raise NoParse(
                f'bad argument at position {index} {obj_json!r}: '
                f'could not decode json array'
            )

class ArgsJsonStringArray(ArgsJson):
    def assert_obj(self, index, obj_json, obj):
        if not isinstance(obj, list):
            raise NoParse(
                f'bad argument at position {index} {obj_json!r}: '
                f'could not decode json array'
            )
        if any(not isinstance(item, str) for item in obj):
            raise NoParse(
                f'bad argument at position {index} {obj_json!r}: '
                f'could not decode json array of strings'
            )

class ArgsJsonTokenUser(ArgsJsonString):
    def transform_obj(self, token):
        try:
            user = USERS_BY_TOKEN[token]
        except KeyError:
            raise BadArgument(f'no user with token {token!r}')
        return user

class ArgsJsonHashUser(ArgsString):
    def transform_string(self, token_hash):
        for user in USERS:
            if user['token_hash'] == token_hash:
                break
        else:
            raise BadArgument(f'no user with token_hash {token_hash!r}')
        return user

def ArgsUser(spec):
    return Str({
        'token': ArgsJsonTokenUser(spec),
        'hash': ArgsJsonHashUser(spec),
    })
