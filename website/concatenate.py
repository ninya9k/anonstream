import os
import time
from website.constants import HLS_TIME, SEGMENTS_DIR, SEGMENT_INIT, VIEW_COUNTING_PERIOD
from website.utils.stream import _is_segment, _segment_number, _get_segments

SEGMENT = 'stream{number}.m4s'
CORRUPTING_SEGMENT = 'corrupt.m4s'
STREAM_TIMEOUT = HLS_TIME + 2 # consider the stream offline after this many seconds without a new segment

# TODO: uncommment this if it becomes useful
#
#CACHE_TIMEOUT = 360 # remove a segment from the cache if it is deleted and this many seconds have passed since it was first created
#
#class SegmentNotCached(Exception):
#    pass
#
#
#class StreamRestarted(Exception):
#    pass
#
#
#class SegmentsCache:
#    def __init__(self, segments_dir, stream_start_path):
#        self.segments_dir = segments_dir
#        self.segments = {}
#        self.lock = threading.Lock()
#        self.stream_start_path = stream_start_path
#        self.corrupting_segment = b''
#        self.stream_start = self.get_stream_start_time(warn=True)
#
#    def get_stream_start_time(self, warn=False):
#        try:
#            start = open(self.stream_start_path).read()
#            start = int(start)
#        except (FileNotFoundError, ValueError):
#            start = None
#        else:
#            self.corrupting_segment = self.corrupting_segment or open(os.path.join(self.segments_dir, CORRUPTING_SEGMENT), 'rb').read()
#        if start == None and warn:
#            print('WARNING: SegmentsCache couldn\'t find when the stream started; it uses this to clear the cache of segments when the stream restarts or ends. The noscript livestream will not work unless we have the stream start time. If you haven\'t started the stream yet, ignore this warning.')
#        return start
#
#    def _purge(self):
#        for segment in set(self.segments):
#            segment_path = os.path.join(self.segments_dir, segment)
#            if not os.path.isfile(segment_path) and int(time.time()) - self.segments[segment]['mtime'] >= CACHE_TIMEOUT:
#                segment_info = self.segments.pop(segment)
#                #print(f'Removed segment {segment} from the cache for inactivity')
#                
#    def read(self, segment, read_size, instance_id):
#        segment_path = os.path.join(self.segments_dir, segment)
#        with self.lock:
#            # ensure we don't cache segments from a previous stream
#            stream_start = self.get_stream_start_time()
#            if stream_start == None:
#                #print('Stream has already ended, clearing cache...')
#                self.stream_start = stream_start
#                self.segments.clear()
#            elif stream_start != self.stream_start:
#                #print('Stream restarted, clearing cache...')
#                self.stream_start = stream_start
#                self.segments.clear()
#                raise StreamRestarted # this is because the video gets corrupted anyway when the stream restarts and you append segments from the new stream to segments from the old stream
#            # TODO: fall back to reading from disk if we can't find the stream start time
#            if self.stream_start == None:
#                raise SegmentNotCached
#
#            # if the segment is not cached, cache it
#            if segment not in self.segments:
#                segment_mtime = os.path.getmtime(segment_path)
#                with open(segment_path, 'rb') as fp:
#                    segment_data = fp.read()
#                self.segments[segment] = {'mtime': int(os.path.getmtime(segment_path)),
#                                          'data': segment_data,
#                                          'interest': {instance_id: 0}}
#
#            # remove all inactive segments
#            self._purge()
#
#            if segment not in self.segments:
#                raise SegmentUnavailable
#
#            # get the chunk that was requested
#            read_offset = self.segments[segment]['interest'].get(instance_id, 0)
#            chunk = self.segments[segment]['data'][read_offset:read_offset + read_size]
#            self.segments[segment]['interest'][instance_id] = read_offset + len(chunk)
#
#            # remove this instance if it no longer wants this segment
#            if read_offset + len(chunk) >= len(self.segments[segment]['data']):
#                self.segments[segment]['interest'].pop(instance_id)
#
#            # remove this segment if it is unwanted
#            if len(self.segments[segment]['interest']) == 0:
#                self.segments.pop(segment)
#
##            print(' SegmentsCache.segments')
##            for segment in self.segments:
##                print(f'{segment}=', {k: self.segments[segment][k] for k in self.segments[segment] if k != 'data'})
#
#            return chunk


def resolve_segment_offset(segment_offset=max(VIEW_COUNTING_PERIOD // HLS_TIME, 2)):
    '''
    Returns the number of the segment at `segment_offset` (1 is most recent segment)
    '''
    segments = _get_segments(sort=True)
    try:
        segment = segments[-min(segment_offset, len(segments))]
    except IndexError:
        return 0
    return _segment_number(segment)

def get_next_segment(after, start_segment):
    start = time.time()
    while True:
        time.sleep(1)
        segments = _get_segments(sort=True)
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

        if time.time() - start >= STREAM_TIMEOUT:
            if after == None:
                raise SegmentUnavailable('timeout waiting for initial segment {SEGMENT_INIT}')
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
        # run this function after sending each segment
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

    def _read(self, n):
        chunk = b''
        while True:
            if self.should_close_connection():
                raise SegmentUnavailable(f'told to close while reading {self.segment}')

            #chunk_chunk = self.segments_cache.read(segment=self.segment, read_size=n - len(chunk), instance_id=self.instance_id)
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
            try:
                next_segment = next(self.segments)
            except SegmentUnavailable:
                self.segment_hook(_segment_number(self.segment))
                raise
            else:
                self.segment_hook(_segment_number(self.segment))
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
            # If you use the cache this becomes very unlikely to happen in
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