import os
import re
import time
from flask import abort
from website.constants import CONFIG, SEGMENTS_DIR, SEGMENTS_M3U8, SEGMENT_INIT, STREAM_TITLE, STALE_PLAYLIST_THRESHOLD

RE_SEGMENT_OR_INIT = re.compile(r'\b(stream(?P<number>\d+)\.m4s|init\.mp4)\b')
RE_SEGMENT = re.compile(r'stream(?P<number>\d+)\.m4s')

def _segment_number(fn):
    if fn == SEGMENT_INIT: return None
    return int(RE_SEGMENT.fullmatch(fn).group('number'))

def _is_segment(fn):
    return bool(RE_SEGMENT.fullmatch(fn))

def get_segments():
    if playlist_is_stale():
        return []
    m3u8 = []
    try:
        with open(SEGMENTS_M3U8) as fp:
            for line in fp.readlines():
                line = line.rstrip()
                if _is_segment(line):
                    m3u8.append(line)
                # the stream has ended, return an empty list
                elif line == '#EXT-X-ENDLIST':
                    m3u8.clear()
                    break
    except FileNotFoundError:
        m3u8.clear()
    m3u8.sort(key=_segment_number)
    return m3u8

def _is_available(fn, m3u8):
    return fn in m3u8

def current_segment():
    segments = get_segments()
    if segments:
        return _segment_number(segments[-1])
    return None

def playlist_is_stale():
    try:
        return time.time() - os.path.getmtime(SEGMENTS_M3U8) >= STALE_PLAYLIST_THRESHOLD
    except FileNotFoundError:
        return True

def is_online():
    return bool(get_segments())

def get_title():
    try:
        return open(STREAM_TITLE).read().strip()
    except FileNotFoundError:
        return ''

def get_start(absolute=True, relative=False):
    start = None
    # if segments exist
    if is_online():
        try:
            # then the stream start at the mtime of init.mp4
            start = os.path.getmtime(os.path.join(SEGMENTS_DIR, SEGMENT_INIT))
        except FileNotFoundError:
            pass
        else:
            # minus the length of 1 segment
            # (because init.mp4 is written to when the first segment is created)
            start = int(start) - CONFIG['stream']['hls_time']

    diff = None if start == None else int(time.time()) - start

    if absolute and relative:
        return start, diff
    elif absolute:
        return start
    elif relative:
        return diff

def token_playlist(token):
    '''
    Append '?token={token}' to each segment in the playlist
    '''
    if playlist_is_stale():
        return []
    m3u8 = []
    with open(SEGMENTS_M3U8) as fp:
        for line in fp.readlines():
            line = line.rstrip()
            line = RE_SEGMENT_OR_INIT.sub(lambda match: f'{match.group()}?token={token}', line)
            m3u8.append(line)
            # the stream has ended, pretend this file doesn't exist
            if line == '#EXT-X-ENDLIST':
                raise FileNotFoundError
    return '\n'.join(m3u8)
