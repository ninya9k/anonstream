import os
import time
from website.constants import CONFIG, SEGMENTS_DIR, SEGMENT_INIT, VIEW_COUNTING_PERIOD
from website.utils.stream import _is_segment, _segment_number, get_segments, is_online

SEGMENT = 'stream{number}.m4s'
CORRUPTING_SEGMENT = 'corrupt.m4s'
STREAM_TIMEOUT = lambda: CONFIG['stream']['hls_time'] * 2 + 2 # consider the stream offline after this many seconds without a new segment

def resolve_segment_offset(segment_offset=1):
    '''
    Returns the number of the segment at `segment_offset` (1 is most recent segment)
    '''
    segments = get_segments()
    try:
        segment = segments[-min(segment_offset, len(segments))]
    except IndexError:
        return 0
    return _segment_number(segment)

def get_next_segment(after, start_segment):
    if not is_online():
        raise SegmentUnavailable(f'stream went offline')
    start = time.time()
    while True:
        time.sleep(0.5)
        segments = get_segments()
        if after == None:
            try:
                if os.path.getsize(os.path.join(SEGMENTS_DIR, SEGMENT_INIT)) > 0: # FFmpeg creates an empty init.mp4 and only writes to it when the first segment exists
                    return SEGMENT_INIT
            except FileNotFoundError:
                pass
        elif after == SEGMENT_INIT:
            if os.path.isfile(os.path.join(SEGMENTS_DIR, start_segment)):
                return start_segment
        else:
            segments = filter(lambda segment: _segment_number(segment) > _segment_number(after), segments)
            try:
                return min(segments, key=_segment_number)
            except ValueError:
                pass

        if time.time() - start >= STREAM_TIMEOUT():
            if after == None:
                raise SegmentUnavailable(f'timeout waiting for initial segment {SEGMENT_INIT}')
            elif after == SEGMENT_INIT:
                raise SegmentUnavailable(f'timeout waiting for start segment {start_segment}')
            else:
                raise SegmentUnavailable(f'timeout searching after {after}')

class SegmentUnavailable(Exception):
    pass


class SegmentsIterator:
    def __init__(self, start_segment, skip_init_segment=False):
        self.start_segment = start_segment
        self.segment = SEGMENT_INIT if skip_init_segment else None

    def __iter__(self):
        return self

    def __next__(self):
        self.segment = get_next_segment(self.segment, self.start_segment)
        return self.segment


class ConcatenatedSegments:
    def __init__(self, start_number, segment_hook=None, corrupt_hook=None, should_close_connection=None):
        # start at this segment, after SEGMENT_INIT
        self.start_number = start_number
        # run this function before sending each segment (if we do it after then if someone gets the most of a segment but then stops, that wouldn't be counted, before = 0 viewers means nobody is retrieving the stream, after = slightly more accurate viewer count but 0 viewers doesn't necessarily mean nobody is retrieving the stream)
        self.segment_hook = segment_hook or (lambda n: None)
        # run this function when we send the corrupting segment
        self.corrupt_hook = corrupt_hook or (lambda: None)
        # run this function before reading files; if it returns True, then stop
        self.should_close_connection = should_close_connection or (lambda: None)

        start_segment = SEGMENT.format(number=start_number)
        self.segments = SegmentsIterator(start_segment=start_segment)

        self._closed = False
        self.segment_read_offset = 0
        self.segment = next(self.segments)
        self.segment_hook(_segment_number(self.segment))

    def _read(self, n):
        chunk = b''
        while True:
            if self.should_close_connection():
                raise SegmentUnavailable(f'told to close while reading {self.segment}')

            try:
                with open(os.path.join(SEGMENTS_DIR, self.segment), 'rb') as fp:
                    fp.seek(self.segment_read_offset)
                    chunk_chunk = fp.read(n - len(chunk))
            except FileNotFoundError:
                raise SegmentUnavailable(f'deleted while reading {self.segment}')

            self.segment_read_offset += len(chunk_chunk)
            chunk += chunk_chunk

            if len(chunk) >= n:
                break

            self.segment_read_offset = 0
            next_segment = next(self.segments)
            self.segment_hook(_segment_number(next_segment))
            self.segment = next_segment
        return chunk

    def read(self, n):
        if self._closed:
            return b''

        try:
            return self._read(n)
        except SegmentUnavailable as e:
            # If a fragment gets interrupted and we start appending whole new
            # fragments after it, the video will get corrupted.
            # This is very likely to happen if you become extremely delayed.
            # It's also likely to happen if the reason for the
            # discontinuity is the livestream restarting.
            # If you cache segments this becomes very unlikely to happen in
            # either case. However, appending fragments from the restarted
            # stream corrupts the video; and skipping ahead lots of fragments
            # will make the video pause for the number of fragments that were
            # skipped. TODO: figure this out.

            # Until this is figured out, it's probably best to just corrupt the
            # video stream so it's clear to the viewer that they have to refresh.

            print('SegmentUnavailable in ConcatenatedSegments.read:', *e.args)
            return self._corrupt(n)

    def _corrupt(self, n):
        # TODO: make this corrupt more reliably (maybe it has to follow a full segment?)
        # Doesn't corrupt when directly after init.mp4
        print('ConcatenatedSegments._corrupt')
        self.corrupt_hook()
        self.close()
        try:
            return open(os.path.join(SEGMENTS_DIR, CORRUPTING_SEGMENT), 'rb').read(n)
        except FileNotFoundError:
            # TODO: try to read the corrupting segment earlier
            return b''

    def close(self):
        self._closed = True
