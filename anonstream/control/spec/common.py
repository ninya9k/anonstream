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
                    f'bad word at position {index}: '
                    f'expected one of {set(self.directives)}, found {word!r}'
                )
            raise NoParse(reason) from e
        else:
            if len(candidates) > 1:
                raise Ambiguous(
                    f'bad word at position {index}: cannot unambiguously '
                    f'match {word!r} against {set(self.directives)}'
                )
        return self.directives[directive], 1, []

class End(Spec):
    def __init__(self, fn):
        self.fn = fn

    def consume(self, words, index):
        if len(words) <= index:
            raise Parsed(self.fn)
        raise NoParse(f'garbage at position {index}: {words[index:]!r}')
