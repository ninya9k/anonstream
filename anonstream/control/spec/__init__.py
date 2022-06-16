class ParseException(Exception):
    pass

class NoParse(ParseException):
    pass

class Ambiguous(ParseException):
    pass

class BadArgument(ParseException):
    pass

class Parsed(Exception):
    pass

class Spec:
    def consume(self, words, index):
        raise NotImplemented
