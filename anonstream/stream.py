import time

import aiofiles
from quart import current_app

from anonstream.segments import get_playlist, Offline
from anonstream.wrappers import ttl_cache_async, with_timestamp
from anonstream.helpers.user import is_watching

CONFIG = current_app.config
USERS = current_app.users

@ttl_cache_async(CONFIG['STREAM_TITLE_CACHE_LIFETIME'])
async def get_stream_title():
    try:
        async with aiofiles.open(CONFIG['STREAM_TITLE']) as fp:
            title = await fp.read(8192)
    except FileNotFoundError:
        title = ''
    return title

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

@with_timestamp
def get_stream_viewership(timestamp):
    return sum(map(lambda user: is_watching(timestamp, user), USERS))

def get_stream_viewership_or_none(uptime):
    viewership = get_stream_viewership()
    return uptime and viewership

def is_online():
    try:
        get_playlist()
    except Offline:
        return False
    else:
        return True
