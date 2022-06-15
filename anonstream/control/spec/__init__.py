class NoParse(Exception):
    pass

class Ambiguous(Exception):
    pass

class Parsed(Exception):
    pass

class Spec:
    def consume(self, words, index):
        raise NotImplemented
