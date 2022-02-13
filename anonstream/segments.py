import asyncio
import os
import re
import time
from collections import OrderedDict

import aiofiles

RE_SEGMENT = re.compile(r'^(?P<index>\d+)\.ts$')

class DirectoryCache:
    def __init__(self, directory, ttl=0.5):
        self.directory = directory
        self.ttl = ttl
        self.expires = None
        self.files = None

    def timer(self):
        return time.monotonic()

    def listdir(self):
        if self.expires is None or self.timer() >= self.expires:
            print(f'[debug @ {time.time():.4f}] listdir()')
            self.files = os.listdir(self.directory)
            self.expires = self.timer() + self.ttl
        return self.files

    def segments(self):
        segments = []
        for fn in self.listdir():
            match = RE_SEGMENT.match(fn)
            if match:
                segments.append((int(match.group('index')), fn))
        segments.sort()
        return OrderedDict(segments)

    def path(self, fn):
        return os.path.join(self.directory, fn)

class CatSegments:
    def __init__(self, directory_cache, token):
        self.directory_cache = directory_cache
        self.token = token
        self.index = max(self.directory_cache.segments())

    async def stream(self):
        while True:
            print(
                f'[debug @ {time.time():.4f}: {self.token}] '
                f'index={self.index} '
                f'segments={tuple(self.directory_cache.segments())}'
            )
            # search for current segment
            for i in range(21):
                segment = self.directory_cache.segments().get(self.index)
                if segment is not None:
                    break
                if i != 20:
                    await asyncio.sleep(0.2)
            else:
                print(
                    f'[debug @ {time.time():.4f}: {self.token}] could not '
                    f'find segment #{self.index} after at least 4 seconds'
                )
                return

            # read current segment
            fn = self.directory_cache.path(segment)
            async with aiofiles.open(fn, 'rb') as fp:
                while chunk := await fp.read(8192):
                    yield chunk

            # increment segment index
            self.index += 1
