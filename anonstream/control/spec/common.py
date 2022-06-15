import json

from anonstream.control.spec import Spec, NoParse, Ambiguous, Parsed
from anonstream.control.spec.utils import get_item, startswith

class Str(Spec):
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
        return self.directives[directive], 1, []

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
    def consume(self, words, index):
        try:
            string = words[index]
        except IndexError:
            raise NoParse(f'incomplete: expected string')
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

class ArgsJsonString(ArgsJson):
    def assert_obj(self, index, obj_json, obj):
        if not isinstance(obj, str):
            raise NoParse(
                f'bad argument at position {index} {obj_json!r}: '
                f'could not decode json string'
            )
