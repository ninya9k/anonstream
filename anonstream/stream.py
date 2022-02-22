import time

from anonstream.segments import get_playlist, Offline

def get_stream_title():
    return 'Stream title'

def get_stream_uptime(rounded=True):
    try:
        playlist, mtime = get_playlist()
    except Offline:
        return None
    else:
        last_modified_ago = time.time() - mtime

        n_segments = playlist.media_sequence + len(playlist.segments)
        duration = playlist.target_duration * n_segments

        uptime = duration + last_modified_ago
        uptime = round(uptime, 2) if rounded else uptime
        return uptime

def is_online():
    try:
        get_playlist()
    except Offline:
        return False
    else:
        return True
