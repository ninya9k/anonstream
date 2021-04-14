import os
import re
import time
from website.constants import SEGMENTS_DIR, SEGMENTS_M3U8, SEGMENT_INIT, STREAM_PIDFILE, STREAM_START, STREAM_TITLE

RE_SEGMENT = re.compile(r'stream(?P<number>\d+).m4s')

def _segment_number(fn):
    if fn == SEGMENT_INIT: return None
    return int(RE_SEGMENT.fullmatch(fn).group('number'))

def _is_segment(fn):
    return bool(RE_SEGMENT.fullmatch(fn))

def _get_segments(sort=False):
    try:
        m3u8 = [line.rstrip() for line in open(SEGMENTS_M3U8).readlines() if _is_segment(line.rstrip())]
    except FileNotFoundError:
        return []

    if sort:
        m3u8.sort(key=_segment_number)
    return m3u8

def _is_available(fn, m3u8):
    return fn in m3u8

def current_segment():
    if is_online():
        segments = _get_segments()
        if len(segments) == 0:
            return None
        last_segment = max(segments, key=_segment_number)
        return _segment_number(last_segment)
    else:
        return None

def is_online():
    # If the pidfile doesn't exist, return False
    try:
        pid = open(STREAM_PIDFILE).read()
        pid = int(pid)
    except (FileNotFoundError, ValueError):
        return False

    # If the process ID doesn't exist, return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False

    # Otherwise return True
    return True

def get_title():
    try:
        return open(STREAM_TITLE).read().strip()
    except FileNotFoundError:
        return ''

def get_start(absolute=True, relative=False):
    try:
        start = open(STREAM_START).read()
        start = int(start)
    except (FileNotFoundError, ValueError):
        start = None

    diff = None if start == None else int(time.time()) - start

    if absolute and relative:
        return start, diff
    elif absolute:
        return start
    elif relative:
        return diff