import hashlib
from website.constants import BACKGROUND_COLOUR
from functools import lru_cache

# functions for calculating constrast between two colours
# https://www2.cs.sfu.ca/CourseCentral/820/li/material/RGB-YUV.pdf
# https://www.accessibility-developer-guide.com/knowledge/colours-and-contrast/how-to-calculate/

def _contrast_numerator(c1):
    l1 = (0.299 * c1[0] + 0.587 * c1[1] + 0.114 * c1[2]) / 256
    return l1 + 0.05

# this is being cached because it is always called with the colours of existing
# users, and we don't need to do the same float division thousands of times
# just for gen_colour to return a single colour
@lru_cache(maxsize=256)
def _contrast_denominator(c2):
    l2 = (0.299 * c2[0] + 0.587 * c2[1] + 0.114 * c2[2]) / 256
    return 1 / (l2 + 0.05)

def _contrast(c1, c2):
    return _contrast_numerator(c1) * _contrast_denominator(c2)

def _distance_sq(c1, c2):
    return sum((i / 256 - j / 256) ** 2 for i, j in zip(c1, c2))

def _gen_colour(seed, background=BACKGROUND_COLOUR):
    '''
    Returns a colour with sufficient contrast to the background colour
    '''
    for _ in range(16): # this loop exits on the first iteration 99.99% of the time (literally)
        seed = hashlib.sha256(seed).digest()
        for i in range(0, len(seed) - len(seed) % 3, 3):
            colour = seed[i:i+3]
            if 1.5 < _contrast(colour, background) < 3:
                break
    return colour, seed

def gen_colour(seed, background=BACKGROUND_COLOUR, *avoid):
    '''
    Returns a colour with sufficient contrast to the background colour
    Tries to make the colour contrast with all the colours in `avoid`
    This function hasn't been analysed for efficiency or anything
    '''
    best_colour, best_score = None, None
    for _ in range(1024):
        colour, seed = _gen_colour(seed, background)
        if len(avoid) == 0:
            score = float('inf')
        elif colour in avoid:
            score = float('-inf')
        else:
            score = sum(_contrast(colour, c) for c in avoid) / len(avoid)
        if 2.5 < score:
            return colour
        if best_score == None or score > best_score:
            best_colour, best_score = colour, score
    return best_colour

def tag(token, length=3):
    '''
    Generates a deterministic pseudorandom tag from a given token
    '''
    digest = hashlib.sha256(token.encode()).digest()
    return f'#{digest.hex()[:length]}'
