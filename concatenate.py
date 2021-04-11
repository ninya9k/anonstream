import re
import os
import time

RE_SEGMENT = re.compile(r'stream(?P<number>\d+).m4s')
SEGMENT_INIT = 'init.mp4'
STREAM_TIMEOUT = 24 # consider the stream offline after this many seconds without a new segment
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
            try:
                return segments[-min(SEGMENT_OFFSET, len(segments))]
            except IndexError:
                pass
        else:
            segments = filter(lambda segment: _segment_number(segment) > _segment_number(after), segments)
        try:
            return min(segments, key=_segment_number)
        except ValueError:
            if time.time() - start >= STREAM_TIMEOUT:
                print(f'SegmentUnavailable in get_next_segment; {after=}')
                raise SegmentUnavailable

def get_segments(segments_dir):
    segments = os.listdir(segments_dir)
    segments = filter(_is_segment, segments)
    segments = sorted(segments, key=_segment_number)
    return segments

class SegmentUnavailable(Exception):
    pass


class SegmentsIterator:
    def __init__(self, segments_dir, skip_init_segment=False):
        self.segments_dir = segments_dir
        self.segment = SEGMENT_INIT if skip_init_segment else None

    def __iter__(self):
        return self

    def __next__(self):
        self.segment = get_next_segment(self.segment, self.segments_dir)
        return self.segment

class ConcatenatedSegments:
    def __init__(self, segments_dir, segment_hook=None):
        self.segment_hook = segment_hook or (lambda n: None)
        self.segments_dir = segments_dir
        self._reset()
    
    def _reset(self, skip_init_segment=False):
        print('ConcatenatedSegments._reset')
        self.segments = SegmentsIterator(self.segments_dir, skip_init_segment=skip_init_segment)
        self.segment = next(self.segments)
        self.segment_read_offset = 0
        self._closed = False

    def _read(self, n):
        chunk = b''
        while True:
            #print(f' {len(chunk)=}, {n=}, {self.segment=}, {self.segment_read_offset=}')
            #print(f' segment {self.segment} exists:', os.path.isfile(os.path.join(self.segments.segments_dir, self.segment)))
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
            except SegmentUnavailable:
                print('SegmentUnavailable in ConcatenatedSegments._read')
                raise
            else:
                self.segment_hook(_segment_number(self.segment))
                self.segment = next_segment
        #print(f'_read EXIT; {len(chunk)=}, {n=}, {self.segment=}, {self.segment_read_offset=}')
        return chunk

    def read(self, n):
        if self._closed:
            return b''

        try:
            return self._read(n)
        except (FileNotFoundError, SegmentUnavailable):
            if self.segment == SEGMENT_INIT:
                self.close()
                return b''
            else:
                # If this interrups a fragment and starts appending whole new
                # fragments after, it will corrupt the video.
                # It appears this is very likely to happen if you become
                # extremely delayed. At least it's clear that you need to
                # refresh the page.
                # If the reason for the discontinuity is the livestream
                # restarting, this is unlikely to happen; it'll continue fine.
                print('DISCONTINUITY in ConcatenatedSegments.read')
                self._reset(skip_init_segment=True)
                return self._read(n)

    def close(self):
        self._closed = True
