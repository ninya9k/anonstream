# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
import random
from math import inf

class NotAColor(Exception):
    pass

RE_COLOR = re.compile(
    r'^#(?P<red>[0-9a-fA-F]{2})(?P<green>[0-9a-fA-F]{2})(?P<blue>[0-9a-fA-F]{2})$'
)

def color_to_colour(color):
    match = RE_COLOR.match(color)
    if not match:
        raise NotAColor
    return (
        int(match.group('red'), 16),
        int(match.group('green'), 16),
        int(match.group('blue'), 16),
    )

def colour_to_color(colour):
    red, green, blue = colour
    return f'#{red:02x}{green:02x}{blue:02x}'

def dot(a, b):
    '''
    Dot product.
    '''
    return sum(i * j for i, j in zip(a, b, strict=True))

def _sc_to_tc(sc):
    '''
    The transformation on [0,1] (from an s-component to a t-component)
    defined at https://www.w3.org/TR/WCAG21/#dfn-relative-luminance.
    '''
    if sc < 0.03928:
        tc = sc / 12.92
    else:
        tc = pow((sc + 0.055) / 1.055, 2.4)
    return tc

def _tc_to_sc(tc):
    '''
    Almost-inverse of _sc_to_tc.

    The function _sc_to_tc is not injective (because of the discontinuity at
    sc=0.03928), thus it has no true inverse.  In this implementation, whenever
    for a given `tc` there are two distinct values of `sc` such that
    sc_to_tc(`sc`)=`tc`, the smaller sc is chosen. (The smaller one is less
    expensive to compute).
    '''
    sc = tc * 12.92
    if sc >= 0.03928:
        sc = pow(tc, 1 / 2.4) * 1.055 - 0.055
    return sc

def get_relative_luminance(colour):
    '''
    Take a colour and return its relative luminance.

    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    '''
    s = map(lambda sc: sc / 255, colour)
    t = map(_sc_to_tc, s)
    return dot((0.2126, 0.7152, 0.0722), t)

def get_colour(t):
    '''
    Take a 3-tuple of channels `t` and return an approximation of a colour
    that when fed into get_relative_luminance would internally cause the
    the variable named "t" to have a value equal to `t`.
    '''
    s = map(_tc_to_sc, t)
    colour = map(lambda sc: round(sc * 255), s)
    return tuple(colour)

def get_contrast(bg, fg):
    '''
    Return the contrast ratio between two colours `bg` and `fg`.

    https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
    '''
    lumas = (
        get_relative_luminance(bg),
        get_relative_luminance(fg),
    )
    return (max(lumas) + 0.05) / (min(lumas) + 0.05)

def generate_colour(seed, bg, min_contrast=4.5, max_contrast=inf, lighter=True):
    '''
    Generate a random colour with a contrast to `bg` in a given interval.

    This works by generating an intermediate 3-tuple `t` and transforming it
    into the returned colour.  Channels of `t` are uniformly distributed, but no
    characteristics of the returned colour are guaranteed to be chosen uniformly
    from the space of possible values.

    If `lighter` is true, the returned colour is forced to have a higher
    relative luminance than `bg`.  This is fine if `bg` is dark; if `bg` is not
    dark, the space of possible returned colours will be a lot smaller (and
    might be empty).  If `lighter` is false, the returned colour is forced to
    have a lower relative luminance than `bg`.

    It's simple to calculate the maximum possible contrast between `bg` and any
    other colour.  (The minimum contrast is always 1.)

    >>> bg = (0x23, 0x23, 0x27)
    >>> luma = get_relative_luminance(bg)
    >>> (luma + 0.05) / 0.05 # maximum contrast for colours with smaller luma
    1.3411743495243844
    >>> 1.05 / (luma + 0.05) # maximum contrast for colours with greater luma
    15.657919499763137

    There are contrast intervals for which the space of possible returned
    colours is empty.  For example a contrast greater than 21 is always
    impossible, but the exact upper bound depends on `bg`.  The desired relative
    luminance of the returned colour must exist in the interval [0,1].  The
    formula for desired luma is given below.  This is for one particular
    contrast but the same formula can be used twice (once with `min_contrast` and
    once with `max_contrast`) to get a range of desired lumas.

    >>> bg_luma = get_relative_luminance(bg)
    >>> desired_luma = (
    ...     contrast * (bg_luma + 0.05) - 0.05
    ...     if lighter else
    ...     (bg_luma + 0.05) / contrast - 0.05
    ... )
    >>> 0 <= desired_luma <= 1
    True
    '''
    r = random.Random(seed)

    if lighter:
        min_desired_luma = min_contrast * (get_relative_luminance(bg) + 0.05) - 0.05
        max_desired_luma = max_contrast * (get_relative_luminance(bg) + 0.05) - 0.05
    else:
        min_desired_luma = (get_relative_luminance(bg) + 0.05) / max_contrast - 0.05
        max_desired_luma = (get_relative_luminance(bg) + 0.05) / min_contrast - 0.05

    V = (0.2126, 0.7152, 0.0722)
    indices = [0, 1, 2]
    r.shuffle(indices)
    i, j, k = indices

    # V[i] * ti + V[j] * 0 + V[k] * 0 <= max_desired_luma
    # V[i] * ti + V[j] * 1 + V[k] * 1 >= min_desired_luma
    ti_upper = (max_desired_luma - V[j] * 0 - V[k] * 0) / V[i]
    ti_lower = (min_desired_luma - V[j] * 1 - V[k] * 1) / V[i]
    ti = r.uniform(max(0, ti_lower), min(1, ti_upper))

    # V[i] * ti + V[j] * tj + V[k] * 0 <= max_desired_luma
    # V[i] * ti + V[j] * tj + V[k] * 1 >= min_desired_luma
    tj_upper = (max_desired_luma - V[i] * ti - V[k] * 0) / V[j]
    tj_lower = (min_desired_luma - V[i] * ti - V[k] * 1) / V[j]
    tj = r.uniform(max(0, tj_lower), min(1, tj_upper))

    # V[i] * ti + V[j] * tj + V[k] * tk <= max_desired_luma
    # V[i] * ti + V[j] * tj + V[k] * tk >= min_desired_luma
    tk_upper = (max_desired_luma - V[i] * ti - V[j] * tj) / V[k]
    tk_lower = (min_desired_luma - V[i] * ti - V[j] * tj) / V[k]
    tk = r.uniform(max(0, tk_lower), min(1, tk_upper))

    t = [None, None, None]
    t[i], t[j], t[k] = ti, tj, tk

    s = map(_tc_to_sc, t)
    colour = map(lambda sc: round(sc * 255), s)
    return tuple(colour)

def get_maximum_contrast(bg, lighter=True):
    '''
    Return the maximum possible contrast between `bg` and any other lighter
    or darker colour.

    If `lighter` is true, restrict to the set of colours whose relative
    luminance is greater than `bg`'s.

    If `lighter` is false, restrict to the set of colours whose relative
    luminance is greater than `bg`'s.
    '''
    luma = get_relative_luminance(bg)
    if lighter:
        max_contrast = 1.05 / (luma + 0.05)
    else:
        max_contrast = (luma + 0.05) / 0.05
    return max_contrast

def generate_maximum_contrast_colour(seed, bg, proportion_of_max=31/32):
    max_lighter_contrast = get_maximum_contrast(bg, lighter=True)
    max_darker_contrast = get_maximum_contrast(bg, lighter=False)

    max_contrast = max(max_lighter_contrast, max_darker_contrast)
    practical_max_contrast = max_contrast * proportion_of_max
    colour = generate_colour(
        seed,
        bg,
        min_contrast=practical_max_contrast,
        max_contrast=practical_max_contrast,
        lighter=max_lighter_contrast > max_darker_contrast,
    )

    return colour
