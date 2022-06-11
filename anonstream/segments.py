# SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import os
import time

import aiofiles
import m3u8
from quart import current_app

from anonstream.wrappers import ttl_cache, with_timestamp

CONFIG = current_app.config

class Offline(Exception):
    pass

class Stale(Exception):
    pass

class UnsafePath(Exception):
    pass

def get_mtime():
    try:
        mtime = os.path.getmtime(CONFIG['SEGMENT_PLAYLIST'])
    except OSError as e:
        raise Stale(f"couldn't stat playlist: {e}") from e
    else:
        mtime_ago = time.time() - mtime
        if mtime_ago >= CONFIG['SEGMENT_PLAYLIST_STALE_THRESHOLD']:
            raise Stale(f'last modified {mtime_ago:.1f}s ago')
    return mtime

@ttl_cache(CONFIG['SEGMENT_PLAYLIST_CACHE_LIFETIME'])
def get_playlist():
    #print(f'[debug @ {time.time():.3f}] get_playlist()')
    try:
        mtime = get_mtime()
    except Stale as e:
        reason, *_ = e.args
        raise Offline(f'stale playlist: {reason}') from e
    else:
        try:
            playlist = m3u8._load_from_file(CONFIG['SEGMENT_PLAYLIST'])
        except OSError:
            raise Offline(f"couldn't read playlist: {e}") from e
        else:
            if playlist.is_endlist:
                raise Offline('playlist ended')
            if len(playlist.segments) == 0:
                raise Offline('empty playlist')

    return playlist, mtime

def get_starting_segment():
    '''
    Instead of choosing the most recent segment, try choosing a segment that
    preceeds the most recent one by a little bit. Doing this increases the
    buffer of initially available video, which makes playback more stable.
    '''
    print(f'[debug @ {time.time():.3f}] get_starting_segment()')
    playlist, _ = get_playlist()
    index = max(0, len(playlist.segments) - CONFIG['SEGMENT_STREAM_INITIAL_BUFFER'])
    return playlist.segments[index]

def get_next_segment(uri):
    '''
    Look for the segment with uri `uri` and return the segment that
    follows it, or None if no such segment exists.
    '''
    #print(f'[debug @ {time.time():.3f}] get_next_segment({uri!r})')
    playlist, _ = get_playlist()
    found = False
    for segment in playlist.segments:
        if found:
            break
        elif segment.uri == uri:
            found = True
    else:
        segment = None
    return segment

async def get_segment_uris(token):
    try:
        segment = get_starting_segment()
    except Offline as e:
        reason, *_ = e.args
        print(
            f'[debug @ {time.time():.3f}: {token=}] '
            f'stream went offline before we could find any segments ({reason})'
        )
        return

    if segment.init_section is not None:
        yield segment.init_section.uri

    while True:
        yield segment.uri

        t0 = time.monotonic()
        while True:
            try:
                next_segment = get_next_segment(segment.uri)
            except Offline as e:
                reason, *_ = e.args
                print(
                    f'[debug @ {time.time():.3f}: {token=}] '
                    f'stream went offline while looking for the '
                    f'segment following {segment.uri!r} ({reason})'
                )
                return
            else:
                if next_segment is not None:
                    segment = next_segment
                    break
                elif time.monotonic() - t0 >= CONFIG['SEGMENT_SEARCH_TIMEOUT']:
                    print(
                        f'[debug @ {time.time():.3f}: {token=}] '
                        f'timed out looking for the segment following '
                        f'{segment.uri!r} '
                        f'(timeout={CONFIG["SEGMENT_SEARCH_TIMEOUT"]}s)'
                    )
                    return
                else:
                    await asyncio.sleep(CONFIG['SEGMENT_SEARCH_COOLDOWN'])

def path_for(uri):
    path = os.path.normpath(
        os.path.join(CONFIG['SEGMENT_DIRECTORY'], uri)
    )
    if os.path.dirname(path) != CONFIG['SEGMENT_DIRECTORY']:
        raise UnsafePath(path)
    return path

async def segments(segment_read_hook=lambda uri: None, token=None):
    print(f'[debug @ {time.time():.3f}: {token=}] entering segment generator')
    async for uri in get_segment_uris(token):
        #print(f'[debug @ {time.time():.3f}: {token=}] {uri=}')
        try:
            path = path_for(uri)
        except UnsafePath as e:
            unsafe_path, *_ = e.args
            print(
                f'[debug @ {time.time():.3f}: {token=}] '
                f'segment {uri=} has {unsafe_path=}'
            )
            break

        segment_read_hook(uri)
        try:
            async with aiofiles.open(path, 'rb') as fp:
                while chunk := await fp.read(8192):
                    yield chunk
        except FileNotFoundError:
            print(
                f'[debug @ {time.time():.3f}: {token=}] '
                f'segment {uri=} at {path=} unexpectedly does not exist'
            )
            break
        except OSError as e:
            print(
                f'[debug @ {time.time():.3f}: {token=}] '
                f'segment {uri=} at {path=} cannot be read: {e}'
            )
            break
    print(f'[debug @ {time.time():.3f}: {token=}] exiting segment generator')
