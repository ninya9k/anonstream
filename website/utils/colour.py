import hashlib
from website.constants import BACKGROUND_COLOUR

def _contrast(c1, c2):
    # https://www2.cs.sfu.ca/CourseCentral/820/li/material/RGB-YUV.pdf
    l1 = (0.299 * c1[0] + 0.587 * c1[1] + 0.114 * c1[2]) / 256
    l2 = (0.299 * c2[0] + 0.587 * c2[1] + 0.114 * c2[2]) / 256
    # https://www.accessibility-developer-guide.com/knowledge/colours-and-contrast/how-to-calculate/
    return (l1 + 0.05) / (l2 + 0.05)

def _distance_sq(c1, c2):
    return sum((i / 256 - j / 256) ** 2 for i, j in zip(c1, c2))

def _gen_colour(seed, background=BACKGROUND_COLOUR):
    '''
    Returns a colour that with sufficient contrast to the background colour
    '''
    while True:
        seed = hashlib.sha256(seed).digest()
        for i in range(0, len(seed) - len(seed) % 3, 3):
            colour = seed[i:i+3]
            if 1.5 < _contrast(colour, background):
                return colour

def gen_colour(seed, background=BACKGROUND_COLOUR, *avoid):
    '''
    Returns a colour that with sufficient contrast to the background colour
    Tries to make the colour contrast with all the colours in `avoid`
    '''
    best_colour, best_score = None, None
    for _ in range(16384):
        colour = _gen_colour(seed, background)
        score = float('inf') if len(avoid) == 0 else sum(_contrast(colour, c) for c in avoid) / len(avoid)
        if 1.25 < score:
            return colour
        if best_score == None or score > best_score:
            best_colour = colour
    return best_colour