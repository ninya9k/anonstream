import hashlib

def _contrast(c1, c2):
    # https://www2.cs.sfu.ca/CourseCentral/820/li/material/RGB-YUV.pdf
    l1 = (0.299 * c1[0] + 0.587 * c1[1] + 0.114 * c1[2]) / 256
    l2 = (0.299 * c2[0] + 0.587 * c2[1] + 0.114 * c2[2]) / 256
    # https://www.accessibility-developer-guide.com/knowledge/colours-and-contrast/how-to-calculate/
    return (l1 + 0.05) / (l2 + 0.05)

def _distance_sq(c1, c2):
    return sum((i / 256 - j / 256) ** 2 for i, j in zip(c1, c2))

def gen_colour(seed, background):
    while True:
        seed = hashlib.sha256(seed).digest()
        colour = seed[:3]
        if 1.5 < _contrast(colour, background):
            return colour
