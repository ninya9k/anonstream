# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import itertools
import operator
import time

import aiofiles
from quart import current_app

from anonstream.segments import get_playlist, Offline
from anonstream.wrappers import ttl_cache_async, with_timestamp
from anonstream.user import get_watching_users

CONFIG = current_app.config
USERS = current_app.users

@ttl_cache_async(CONFIG['STREAM_TITLE_CACHE_LIFETIME'])
async def get_stream_title():
    try:
        async with aiofiles.open(CONFIG['STREAM_TITLE']) as fp:
            title = await fp.read(8192)
    except OSError as e:
        print(f'WARNING: could not read stream title: {e}')
        title = ''
    return title

async def set_stream_title(title):
    async with aiofiles.open(CONFIG['STREAM_TITLE'], 'w') as fp:
        await fp.write(title)

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

@with_timestamp()
def get_raw_viewership(timestamp):
    users = get_watching_users(timestamp)
    return max(
        map(operator.itemgetter(0), zip(itertools.count(1), users)),
        default=0,
    )

def get_stream_uptime_and_viewership(rounded=True, for_websocket=False):
    uptime = get_stream_uptime(rounded=rounded)
    if not for_websocket:
        viewership = None if uptime is None else get_raw_viewership()
        result = (uptime, viewership)
    elif uptime is None:
        result = None
    else:
        result = {
            'uptime': uptime,
            'viewership': get_raw_viewership(),
        }
    return result

def is_online():
    try:
        get_playlist()
    except Offline:
        return False
    else:
        return True
