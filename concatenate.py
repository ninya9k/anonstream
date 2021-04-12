import re
import os
import time
import threading
import secrets

RE_SEGMENT = re.compile(r'stream(?P<number>\d+).m4s')
SEGMENT_INIT = 'init.mp4'
CACHE_TIMEOUT = 0 # remove segments from the cache if it is deleted and this many seconds have passed since it was first created # it's zero because the cache is unnecessary at this point; we're only corrupting video streams, not repairing them
CORRUPTING_SEGMENT = 'corrupt.m4s'

# TODO: sometimes the stream will restart so StreamOffline will be raised, but you could just start appending the segments from the new stream instead of closing the connection
def _segment_number(fn):
    if fn == SEGMENT_INIT: return None
    return int(RE_SEGMENT.fullmatch(fn).group('number'))

def _is_segment(fn):
    return bool(RE_SEGMENT.fullmatch(fn))

def get_next_segment(after, segments_dir, segment_offset, stream_timeout):
    start = time.time()
    while True:
        time.sleep(1)
        segments = get_segments(segments_dir)
        if after == None:
            return SEGMENT_INIT
        elif after == SEGMENT_INIT:
            try:
                return segments[-min(segment_offset, len(segments))]
            except IndexError:
                pass
        else:
            segments = filter(lambda segment: _segment_number(segment) > _segment_number(after), segments)
        try:
            return min(segments, key=_segment_number)
        except ValueError:
            if time.time() - start >= stream_timeout:
                print(f'SegmentUnavailable in get_next_segment; {after=}')
                raise SegmentUnavailable

def get_segments(segments_dir):
    segments = os.listdir(segments_dir)
    segments = filter(_is_segment, segments)
    segments = sorted(segments, key=_segment_number)
    return segments

class SegmentUnavailable(Exception):
    pass


class SegmentNotCached(Exception):
    pass


class StreamRestarted(Exception):
    pass


class SegmentsIterator:
    def __init__(self, segments_dir, segment_offset, stream_timeout, skip_init_segment=False):
        self.segment_offset = segment_offset
        self.stream_timeout = stream_timeout
        self.segments_dir = segments_dir
        self.segment = SEGMENT_INIT if skip_init_segment else None

    def __iter__(self):
        return self

    def __next__(self):
        self.segment = get_next_segment(self.segment, self.segments_dir, self.segment_offset, self.stream_timeout)
        return self.segment


class SegmentsCache:
    def __init__(self, segments_dir, stream_start_path):
        self.segments_dir = segments_dir
        self.segments = {}
        self.lock = threading.Lock()
        self.stream_start_path = stream_start_path
        self.corrupting_segment = b''
        self.stream_start = self.get_stream_start_time(warn=True)

    def get_stream_start_time(self, warn=False):
        try:
            start = open(self.stream_start_path).read()
            start = int(start)
        except (FileNotFoundError, ValueError):
            start = None
        else:
            self.corrupting_segment = self.corrupting_segment or open(os.path.join(self.segments_dir, CORRUPTING_SEGMENT), 'rb').read()
        if start == None and warn:
            print('WARNING: SegmentsCache couldn\'t find when the stream started; it uses this to clear the cache of segments when the stream restarts or ends. The noscript livestream will not work unless we have the stream start time. If you haven\'t started the stream yet, ignore this warning.')
        return start

    def _purge(self):
        for segment in set(self.segments):
            segment_path = os.path.join(self.segments_dir, segment)
            if not os.path.isfile(segment_path) and int(time.time()) - self.segments[segment]['mtime'] >= CACHE_TIMEOUT:
                segment_info = self.segments.pop(segment)
                #print(f'Removed segment {segment} from the cache for inactivity')
                
    def read(self, segment, read_size, instance_id):
        segment_path = os.path.join(self.segments_dir, segment)
        with self.lock:
            # ensure we don't cache segments from a previous stream
            stream_start = self.get_stream_start_time()
            if stream_start == None:
                #print('Stream has already ended, clearing cache...')
                self.stream_start = stream_start
                self.segments.clear()
            elif stream_start != self.stream_start:
                #print('Stream restarted, clearing cache...')
                self.stream_start = stream_start
                self.segments.clear()
                raise StreamRestarted # this is because the video gets corrupted anyway when the stream restarts and you append segments from the new stream to segments from the old stream
            # TODO: fall back to reading from disk if we can't find the stream start time
            if self.stream_start == None:
                raise SegmentNotCached

            # if the segment is not cached, cache it
            if segment not in self.segments:
                segment_mtime = os.path.getmtime(segment_path)
                with open(segment_path, 'rb') as fp:
                    segment_data = fp.read()
                self.segments[segment] = {'mtime': int(os.path.getmtime(segment_path)),
                                          'data': segment_data,
                                          'interest': {instance_id: 0}}

            # get the chunk that was requested
            read_offset = self.segments[segment]['interest'].get(instance_id, 0)
            chunk = self.segments[segment]['data'][read_offset:read_offset + read_size]
            self.segments[segment]['interest'][instance_id] = read_offset + len(chunk)

            # remove this instance if it no longer wants this segment
            if read_offset + len(chunk) >= len(self.segments[segment]['data']):
                self.segments[segment]['interest'].pop(instance_id)

            # remove this segment if it is unwanted
            if len(self.segments[segment]['interest']) == 0:
                self.segments.pop(segment)

            # remove all inactive segments
            self._purge()

#            print(' SegmentsCache.segments')
#            for segment in self.segments:
#                print(f'{segment}=', {k: self.segments[segment][k] for k in self.segments[segment] if k != 'data'})

            return chunk


class ConcatenatedSegments:
    def __init__(self, segments_dir, segments_cache, segment_offset=4, stream_timeout=24, segment_hook=None):
        self.instance_id = secrets.token_hex(4)
        self.segments_cache = segments_cache

        # start this many segments back from now (1 is most recent segment)
        self.segment_offset = segment_offset
        # consider the stream offline after this many seconds without a new segment
        self.stream_timeout = stream_timeout

        self.segments_dir = segments_dir
        self.segment_hook = segment_hook or (lambda n: None)
        self._closed = False
        self._reset()
    
    def _reset(self, skip_init_segment=False):
        print('ConcatenatedSegments._reset')
        self.segments = SegmentsIterator(self.segments_dir, segment_offset=self.segment_offset, stream_timeout=self.stream_timeout, skip_init_segment=skip_init_segment)
        try:
            self.segment = next(self.segments)
        except SegmentUnavailable:
            print('SegmentUnavailable in ConcatenatedSegments._reset')
            self.close()

    def _read(self, n):
        chunk = b''
        while True:
            #print(f' {len(chunk)=}, {n=}, {self.segment=}, {self.segment_read_offset=}')
            #print(f' segment {self.segment} exists:', os.path.isfile(os.path.join(self.segments.segments_dir, self.segment)))
            chunk_chunk = self.segments_cache.read(segment=self.segment,
                                                   read_size=n - len(chunk),
                                                   instance_id=self.instance_id)
            chunk += chunk_chunk

            if len(chunk) >= n:
                break

            try:
                next_segment = next(self.segments)
            except SegmentUnavailable:
                print('SegmentUnavailable in ConcatenatedSegments._read')
                self.segment_hook(_segment_number(self.segment))
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
        except (SegmentNotCached, StreamRestarted):
            print('SegmentNotCached or StreamRestarted in ConcatenatedSegments.read: unable to repair fmp4 stream')
            # TODO: find a way to remove the StreamRestarted exception
            return self._corrupt(n)
        except (FileNotFoundError, SegmentUnavailable):
            print('FileNotFoundError or SegmentUnavailable in ConcatenatedSegments.read')
            if self.segment == SEGMENT_INIT:
#                # this is here so the video gets corrupted
#                # TODO: find a way to corrupt the video without erroneously
#                #       counting views as this does
#                self._reset(skip_init_segment=True)
#                return self._read(n)

                return self._corrupt(n)
            else:
                # If fragment gets interrupted and we start appending whole new
                # fragments after it, the video will get corrupted.
                # It appears this is very likely to happen if you become
                # extremely delayed. At least it's clear that you need to
                # refresh the page.
                # It's also likely to happen if the reason for the
                # discontinuity is the livestream restarting.
                # If you use the cache this becomes very unlikely to happen in
                # either case.

                # In the browser the video pauses for the amount of time that
                # we skip here; TODO: find a way to make it instantaneous,
                # probably something to do with timestamps in the mp4 fragments
                #print('DISCONTINUITY in ConcatenatedSegments.read')
                #self._reset(skip_init_segment=True)
                #return self._read(n)

                # Until this is figured out, it's probably best to just corrupt
                # the video stream so it's clear to the viewer they must refresh.
                return self._corrupt(n)

    def _corrupt(self, n):
        print('Corrupting video')
        self.close()
        return self.segments_cache.corrupting_segment[:n]

    def close(self):
        self._closed = True
