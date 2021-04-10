import re
import os
import time

RE_SEGMENT = re.compile(r'stream(?P<number>\d+).m4s')
SEGMENT_INIT = 'init.mp4'
STREAM_TIMEOUT = 12 # stop looking for new segments and throw an error after this many seconds
SEGMENT_OFFSET = 4  # start this many segments back from now (1 is most recent segment)

def _segment_number(fn):
    if fn == SEGMENT_INIT: return None
    return int(RE_SEGMENT.fullmatch(fn).group('number'))

def _is_segment(fn):
    return bool(RE_SEGMENT.fullmatch(fn))

def get_next_segment(after, segments_dir):
    start = time.time()
    while True:
        time.sleep(1)
        segments = get_segments(segments_dir)
        if after == None:
            return SEGMENT_INIT
        elif after == SEGMENT_INIT:
            return segments[-min(SEGMENT_OFFSET, len(segments))]
        else:
            segments = filter(lambda segment: _segment_number(segment) > _segment_number(after), segments)
        try:
            return min(segments, key=_segment_number)
        except ValueError:
            if time.time() - start >= STREAM_TIMEOUT:
                print(f'StreamOffline in get_next_segment; {after=}')
                raise StreamOffline

def get_segments(segments_dir):
    segments = os.listdir(segments_dir)
    segments = filter(_is_segment, segments)
    segments = sorted(segments, key=_segment_number)
    return segments

class StreamOffline(Exception):
    pass


class SegmentsIterator:
    def __init__(self, segments_dir):
        self.segments_dir = segments_dir
        self.segment = None

    def __iter__(self):
        return self

    def __next__(self):
        self.segment = get_next_segment(self.segment, self.segments_dir)
        return self.segment

class ConcatenatedSegments:
    def __init__(self, segments_dir, segment_hook=None):
        self.segments = SegmentsIterator(segments_dir)
        self.segment = next(self.segments)
        self.segment_read_offset = 0
        self.segment_hook = segment_hook or (lambda n: None)
    
    def _read(self, n):
        chunk = b''
        while len(chunk) < n:
            #print(f' {len(chunk)=}, {n=}, {self.segment=}, {self.segment_read_offset=}')
            with open(os.path.join(self.segments.segments_dir, self.segment), 'rb') as fp:
                fp.seek(self.segment_read_offset)
                chunk_chunk = fp.read(n - len(chunk))
                self.segment_read_offset += len(chunk_chunk)
                chunk += chunk_chunk

            if len(chunk) >= n:
                break

            self.segment_read_offset = 0
            try:
                next_segment = next(self.segments)
            except StreamOffline:
                print('StreamOffline in self._read')
                self.close()
                break
            else:
                self.segment_hook(_segment_number(self.segment))
                self.segment = next_segment
                self._previous_read = int(time.time())
        #print(f'_read EXIT; {len(chunk)=}, {n=}, {self.segment=}, {self.segment_read_offset=}')
        return chunk

    def read(self, n):
        try:
            return self._read(n)
        except FileNotFoundError:
            print('StreamOffline in self.read')
            raise StreamOffline

    def close(self):
        pass
