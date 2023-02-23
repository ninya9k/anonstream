# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

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
