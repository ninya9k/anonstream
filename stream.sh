# adjust these parameters to your screen
BOX_WIDTH=1920         # pixels
BOX_HEIGHT=1080        # pixels
BOX_OFFSET_X=0         # pixels
BOX_OFFSET_Y=0         # pixels

VIDEO_HEIGHT=360       # pixels
VIDEO_WIDTH=$(echo "$VIDEO_HEIGHT * $BOX_WIDTH / $BOX_HEIGHT / 2 * 2" | bc) # ensures even width, required for yuv420p

VIDEO_BITRATE=200      # kbit/s
AUDIO_BITRATE=64       # kbit/s
AUDIO_CHANNELS=1       # channels

FRAMERATE=50           # fps

HLS_TIME=10            # seconds per segment
DELETION_THRESHOLD=240 # seconds until segments are deleted
HLS_LIST_SIZE=$(echo $DELETION_THRESHOLD / $HLS_TIME | bc)

mkdir -p stream
rm stream/*

# This shell script's process ID, so we can tell if the stream is online or not
echo $$ > stream/pid.txt

# This exists so we can corrupt video streams of viewers who are too delayed
ffmpeg -f lavfi -i color=size="$BOX_WIDTH"x"$BOX_HEIGHT":rate=$FRAMERATE:color=black \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -t 1 \
    -f hls -hls_init_time 0 -hls_time $HLS_TIME -hls_list_size $HLS_LIST_SIZE -hls_flags delete_segments -hls_segment_type fmp4 \
    -map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
    stream/corrupt.m3u8
rm stream/corrupt.m3u8 stream/init.mp4
mv stream/corrupt0.m4s stream/corrupt.m4s

# The current time, so we know when the stream started
date +%s > stream/start.txt

# This is the command you should edit
ffmpeg -thread_queue_size 2048 -video_size "$BOX_WIDTH"x"$BOX_HEIGHT" -framerate $FRAMERATE -f x11grab -i :0.0+$BOX_OFFSET_X,$BOX_OFFSET_Y \
    -thread_queue_size 2048 -f pulse -i default \
    -c:v libx264 -b:v "$VIDEO_BITRATE"k -tune zerolatency -preset slower -g $FRAMERATE -sc_threshold 0 -pix_fmt yuv420p \
    -filter:v scale=$VIDEO_WIDTH:$VIDEO_HEIGHT,"drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf:text='%{gmtime}':fontcolor=white@0.75:box=1:boxborderw=2:boxcolor=black@0.5:fontsize=24:x=8:y=6" \
    -c:a aac -b:a "$AUDIO_BITRATE"k -ac $AUDIO_CHANNELS \
    -f hls -hls_init_time 0 -hls_time $HLS_TIME -hls_list_size $HLS_LIST_SIZE -hls_flags delete_segments -hls_segment_type fmp4 \
    -map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
    stream/stream.m3u8


# TODO: low-latency HLS
# https://stackoverflow.com/a/63229182/15580043
# https://github.com/video-dev/hls.js/projects/7
# https://www.ffmpeg.org/ffmpeg-formats.html#dash-2
# https://github.com/video-dev/hls.js/issues/2861


# software encoding
#    -c:v libx264 -crf 31 -maxrate "$VIDEO_BITRATE"k -bufsize 1M -tune zerolatency -preset slower -g $FRAMERATE -sc_threshold 0 -pix_fmt yuv420p \
#    -c:v libx264 -b:v "$VIDEO_BITRATE"k -tune zerolatency -preset slower -g $FRAMERATE -sc_threshold 0 -pix_fmt yuv420p \

# example Nvidia hardware encoding; see https://trac.ffmpeg.org/wiki/HWAccelIntro
#    -c:v h264_nvenc -rc cbr_ld_hq -b:v "$VIDEO_BITRATE"k -preset llhp -g $FRAMERATE -sc_threshold 0 -pix_fmt yuv420p \


# this is the deprecated version of the timestamp; it shows local time
#    -vf drawtext="expansion=strftime:fontfile='/usr/share/fonts/cantarell/Cantarell-Light.otf':fontsize=128:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=1:text='%T':x=80:y=8" \

# links about overlaying a timestamp
# https://unix.stackexchange.com/questions/508194/how-to-embed-current-time-with-ffmpeg
# https://einar.slaskete.net/2011/09/05/adding-time-stamp-overlay-to-video-stream-using-ffmpeg/
# https://video.stackexchange.com/questions/28999/how-to-burn-timestamp-in-video-with-different-date-format-using-ffmpeg
# https://superuser.com/questions/1020102/adding-a-timestamp-on-frames-captured-using-ffmpeg


# DASH
# DASH can do multiple video/audio streams at different bandwidths
# dashjs didn't work easily in Tor Browser, someone else can figure it out
# TODO: find DASH equivalent of -hls_flags delete_segments
#
#VIDEO_HEIGHT_0=420       # pixels
#VIDEO_WIDTH_0=$(echo "$VIDEO_HEIGHT_0 * 16 / 9 / 2 * 2" | bc)
#VIDEO_WIDTH_1=$(echo "$VIDEO_HEIGHT_1 * 16 / 9 / 2 * 2" | bc)
#VIDEO_BITRATE_0=400    # kbit/s
#VIDEO_BITRATE_1=200    # kbit/s
#
#ffmpeg -thread_queue_size 2048 -video_size "$BIX_WIDTH"x"$BOX_HEIGHT" -framerate $FRAMERATE -f x11grab -i :0.0+$BOX_OFFSET_X,$BOX_OFFSET_Y \
#    -thread_queue_size 2048 -f pulse -i default \
#    -map 0:v -map 0:v -map 1:a \
#    -c:v:0 h264 -b:v "$VIDEO_BITRATE_0"k -preset slow -g $FRAMERATE -sc_threshold 0 -pix_fmt yuv420p \
#    -c:v:1 h264 -b:v "$VIDEO_BITRATE_1"k -preset slow -g $FRAMERATE -sc_threshold 0 -pix_fmt yuv420p \
#    -filter:v:0 scale=$VIDEO_WIDTH_0:$VIDEO_HEIGHT_0,"drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf:text='%{gmtime}':fontcolor=white@0.75:box=1:boxborderw=2:boxcolor=black@0.5:fontsize=24:x=8:y=6" \
#    -filter:v:1 scale=$VIDEO_WIDTH_1:$VIDEO_HEIGHT_1,"drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf:text='%{gmtime}':fontcolor=white@0.75:box=1:boxborderw=2:boxcolor=black@0.5:fontsize=24:x=8:y=6" \
#    -c:a aac -b:a "$AUDIO_BITRATE"k -ac $AUDIO_CHANNELS \
#    -f dash -hls_init_time 0 -hls_time $HLS_TIME -hls_list_size $HLS_LIST_SIZE -adaptation_sets "id=0,streams=v  id=1,streams=a" -ldash 1 \
#    -map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
#    stream/stream.mpd
