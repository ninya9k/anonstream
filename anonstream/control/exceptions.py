class Exit(Exception):
    pass

class UnknownMethod(Exception):
    pass

class UnknownCommand(Exception):
    pass

class UnknownArgument(Exception):
    pass

class BadArgument(Exception):
    pass

class Incomplete(Exception):
    pass

class Garbage(Exception):
    pass

class Failed(Exception):
    pass
