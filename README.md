# onion-livestreaming

Recipe for livestreaming over the Tor network

![Screenshot of the livestream web interface](demo.png)

This was originally made for fun over the course of five days and hence sloppiness may pervade.

* [Repo on GitHub](https://github.com/ninya9k/onion-livestreaming)
* [Repo on GitLab](https://gitlab.com/ninya9k/onion-livestreaming)

This works on Linux, and should work on macOS and Windows with some tweaking. Look at the [setup tutorial](#tutorial).

## Dependencies
* Tor
* FFmpeg
* [Flask](https://github.com/pallets/flask)
* [captcha](https://github.com/lepture/captcha)
* [Flask-HTTPAuth](https://github.com/miguelgrinberg/Flask-HTTPAuth) (to identify the broadcaster in chat)
* [Flask-Compress](https://github.com/colour-science/flask-compress) (should probably be optional)
* Knowledge of FFmpeg and Tor

## Features
* Twitch-looking mobile-friendly web interface
* Change stream title as you're streaming
* Viewer count
* Stream on/off indicator and playback error messages with prompts to refresh
* Chat with custom names & tripcodes
* Ban/unban chatters & hide messages
* Flood detection / liberal captcha
* Shows stream uptime
* List of users watching / not watching
* Optionally uses videojs (append `?videojs=1` to the URL to enable it)
* With videojs disabled, you can scrub backwards and forwards on the video timeline. If you scrub to the end (the most recent segment), you can achieve really quite low latency, as low as 3 seconds.
* Works without JavaScript
* Works without cookies

## Issues
* CSS is spaghetti (e.g. the PureCSS framework is used sometimes when it might not need be)
* AFAIK the FFmpeg command in `stream.sh` only works on Linux, change it for other OSs
* Slow (if videojs is enabled). Using videojs is slower because you have to make many separate GET requests, without it you only need to make one. If you lower the HLS segment size to something like 2 seconds, you get very low latency without videojs (smallest i've got is 3 seconds) but with videojs the stream becomes unwatchable because of the overhead of each GET request you have to make. The stream delay is >30 seconds with videojs and >3 seconds without it. Hopefully this will decrease when congestion control gets into Tor: https://youtu.be/watch?v=zQDbfHSjbnI. ([This article](https://www.martin-riedl.de/2020/04/17/using-ffmpeg-as-a-hls-streaming-server-part-8-reducing-delay/) explains what causes HLS to have latency.)
* Slow chat (uses meta refresh); will be better once websockets is implemented (only with JavaScript enabled though)


* Doesn't use low-latency HLS

## How it works

* FFmpeg creates an HLS stream
* Flask creates a website interface for the stream
* tor makes the website accessible at an onion address

## Explanation of the FFmpeg command in `stream.sh`

The FFmpeg command in `stream.sh` was based on [this series of articles by Martin Riedl](https://www.martin-riedl.de/2020/04/17/using-ffmpeg-as-a-hls-streaming-server-overview/).

### video input (differs between OSs)
`-thread_queue_size 2048 -video_size "$BOX_WIDTH"x"$BOX_HEIGHT" -framerate $FRAMERATE -f x11grab -i :0.0+$BOX_OFFSET_X,$BOX_OFFSET_Y`
* `-thread_queue_size 2048` prevents ffmpeg from giving some warnings
* `-video_size "$BOX_WIDTH"x"$BOX_HEIGHT"` sets the size of the video
* `-framerate $FRAMERATE` sets the framerate of the video
* `-f x11grab` tells ffmpeg to use the `x11grab` device, used for recording the screen on Linux
* `-i :0.0+$BOX_OFFSET_X,$BOX_OFFSET_Y` sets the x- and y-offset for the screen recording

### audio input (differs between OSs)
`-thread_queue_size 2048 -f pulse -i default`

### video encoding
`-c:v libx264 -b:v "$VIDEO_BITRATE"k -tune zerolatency -preset slower -g $FRAMERATE -sc_threshold 0 -pix_fmt yuv420p`

### video filters
`-filter:v scale=$VIDEO_WIDTH:$VIDEO_HEIGHT,"drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf:text='%{gmtime}':fontcolor=white@0.75:box=1:boxborderw=2:boxcolor=black@0.5:fontsize=24:x=8:y=6"`
* `scale=$VIDEO_WIDTH:$VIDEO_HEIGHT` scales the video to the desired size
* `drawtext...` draws the date and time in the top left
* you might need to change the font `/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf` if you're on macOS and definitely if you're on Windows

### audio encoding
`-c:a aac -b:a "$AUDIO_BITRATE"k -ac $AUDIO_CHANNELS`

### HLS configuration
`-f hls -hls_init_time 0 -hls_time $HLS_TIME -hls_list_size $HLS_LIST_SIZE -hls_flags delete_segments -hls_segment_type fmp4`

### strip all metadata
`-map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact`

### output
`stream/stream.m3u8`

## Tutorial

To run this yourself, get this source code. As the project currently exists you might need to change some things:

`stream.sh` as it exists in this repo is set up to record your screen and system audio on Linux. See https://trac.ffmpeg.org/wiki/Capture/Desktop for the syntax for different OSs.

* If you're on Windows `stream.sh` will be wrong for you and so will all the fonts in `config.json`. `stream.sh` uses `$$` to get its process ID, you'll have to use the Windows equivalent.
* If you're on macOS `stream.sh` might need to be changed a bit and you might not have the fonts in `config.json`.
* If you're on Linux `stream.sh` will probably be alright but you might not have all the fonts in `config.json`.

As an aside: you can change the command in stream.sh to record anything you want, it doesn't have to be just your screen and system audio. If you want to change stuff around, just know that all that's required is: (1) `stream/pid.txt` contains `stream.sh`'s process ID, (2) `stream/start.txt` contains the time the stream started, (3) HLS segments appear as `stream/stream*.m4s`, (4) `stream/init.mp4` is the inital HLS segment, and (5) `stream/stream.m3u8` is the HLS playlist. (All this is taken care of in `stream.sh` by default.)

Assuming your FFmpeg command is working, this is what you have to do.

### Start streaming

#### FFmpeg

Go to the project root and type `sh stream.sh`. This starts the livestream.

#### Flask
Go to the project root and type `flask run`. This starts the websever.

#### tor

Now your webserver is running on port 5000 (or whichever port you set it to, if you did that). We need to tell tor to create a hidden service and to point it at port 5000.

In your [torrc](https://support.torproject.org/tbb/tbb-editing-torrc/), add these two lines
```
HiddenServiceDir $PROJECT_ROOT/hidden_service
HiddenServicePort 80 127.0.0.1:5000
```
where `$PROJECT_ROOT` is the root folder of this project. When you reload tor it will create the `hidden_service` directory and your website will be online. Your onion address is in `hidden_service/hostname`. You only need to do this once.

### While streaming

To appear as the broadcaster in chat, go to `/broadcaster` and log in with the username `broadcaster` and the password printed in your terminal when you started Flask.

You can change the stream title while streaming and it will update for all viewers. Edit `title.txt` to do that.

If you restart FFmpeg while you're streaming, viewers will have to refresh the page. All viewers are prompted to refresh the page.

### Stop streaming

To stop streaming, stop FFmpeg. You can delete the files in `stream/` if you want. To start streaming again just rerun `stream.sh`.

If you restart Flask, the chat will be cleared, you'll have to log in again, and everyone else will have to do the captcha again.
