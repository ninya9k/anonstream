def get_item(index, words):
    try:
        word = words[index]
    except IndexError:
        word = None
    else:
        if not word:
            raise NoParse(f'empty word at position {index}')
    return word

def startswith(string, prefix):
    if string is None or prefix is None:
        return string is prefix
    return string.startswith(prefix)
