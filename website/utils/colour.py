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
    CONTRAST_LOW, CONTRAST_HIGH = 1.5, 3.0
    CONTRAST_MIDDLE = (CONTRAST_LOW + CONTRAST_HIGH) / 2
    best_colour, best_score = None, None
    # this loop exits on the first iteration 99.99% of the time (literally)
    for _ in range(4):
        seed = hashlib.sha256(seed).digest()
        for i in range(0, len(seed) - len(seed) % 3, 3):
            colour = seed[i:i+3]
            colour_contrast = _contrast(colour, background)
            if CONTRAST_LOW < _contrast(colour, background) < CONTRAST_HIGH:
                best_colour = colour
                break
            score = abs(colour_contrast - CONTRAST_MIDDLE)
            if best_score == None or score < best_score:
                best_colour, best_score = colour, score
    return best_colour, seed

def gen_colour(seed, background=BACKGROUND_COLOUR, *avoid):
    '''
    Returns a colour with sufficient contrast to the background colour
    Tries to make the colour a little different from all the colours in `avoid`
    '''
    best_colour, best_score = None, None
    for _ in range(4):
        colour, seed = _gen_colour(seed, background)
        if len(avoid) == 0:
            score = float('inf')
        elif colour in avoid:
            score = float('-inf')
        else:
            score = sum(_distance_sq(colour, c) for c in avoid) / len(avoid)
        if best_score == None or score > best_score:
            best_colour, best_score = colour, score
    return best_colour

def tag(token, length=3):
    '''
    Generates a deterministic pseudorandom tag from a given token
    '''
    digest = hashlib.sha256(token.encode()).digest()
    return f'#{digest.hex()[:length]}'
