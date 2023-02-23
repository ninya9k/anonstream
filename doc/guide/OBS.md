### OBS Studio

anonstream considers the stream online when new video segments are
actively being created.  It knows which segments are new by examining
the segment playlist: an HLS playlist located by default at
`stream/stream.m3u8`.  Software like FFmpeg and OBS can write to this
file for you.  This guide is for OBS Studio.  (An example that uses
FFmpeg instead is [at the bottom](#ffmpeg-example).)

Install OBS Studio.  If the autoconfiguration wizard prompts you to
choose a third-party service, ignore it since we're not going to be
using a third-party service.

Click `Settings` and set these:

* Advanced
  * Recording
    * Filename Formatting: `stream`
    * Overwrite if file exists: yes
* Video
  * Output (Scaled) Resolution: `960x540` or lower, or whatever you want
  * Common FPS Values: any integer framerate (e.g. 30 or 60)
* Output
  * Output Mode: `Advanced`
  * Recording:
    ```
    +----------------------------+-------------------------------------+
    | Field                      | Value                               |
    +============================+=====================================+
    | Type                       | `Custom Output (FFmpeg)`            |
    +----------------------------+-------------------------------------+
    | FFmpeg Output Type         | `Output to File`                    |
    +----------------------------+-------------------------------------+
    | File path or URL           | same as the `segments/directory`    |
    |                            | option in config.toml, but make it  |
    |                            | an absolute path                    |
    +----------------------------+-------------------------------------+
    | Container Format           | `hls`                               |
    +----------------------------+-------------------------------------+
    | Muxer Settings (if any)    | `hls_init_time=0 hls_time=2 `       |
    |                            | `hls_list_size=120 `                |
    |                            | `hls_flags=delete_segments `        |
    |                            | `hls_segment_type=fmp4`             |
    +----------------------------+-------------------------------------+
    | Video bitrate              | `420 Kbps` or lower, or whatever    |
    |                            | you want                            |
    +----------------------------+-------------------------------------+
    | Keyframe interval (frames) | `framerate` * `hls_time`, e.g. for  |
    |                            | 60fps and an `hls_time` of 2        |
    |                            | seconds, set this to 120            |
    +----------------------------+-------------------------------------+
    | Video Encoder              | libx264, or an H.264 hardware       |
    |                            | encoder (e.g. `h264_nvenc` for      |
    |                            | Nvidia, [see here][hwaccel])        |
    +----------------------------+-------------------------------------+
    | Audio Bitrate              | `96 Kbps`, or whatever you want     |
    +----------------------------+-------------------------------------+
    | Audio Encoder              | `aac`                               |
    +----------------------------+-------------------------------------+
    ```

> *If this table looks garbled, read this file as plaintext or [click
> here][plaintext] and scroll to the bottom.*

To start streaming click `Start Recording`.

When OBS is recording, segments older than four minutes will be
regularly deleted.  When OBS stops recording, the last four minutes
worth of segments will remain the segments directory.  (You can change
how many segments are kept by modifying the `hls_list_size` option in
the muxer settings.)  When OBS is not recording, you can delete the
files in the segments directory without consequence.  Old segments will
never be sent over the network even if they are not deleted.

### FFmpeg example

This FFmpeg command is basically equivalent to the OBS settings above.
The input (`-i ...`) can be anything, e.g. to screen record see
<https://trac.ffmpeg.org/wiki/Capture/Desktop>.

```sh
ffmpeg \
-re -i somevideo.mp4 \
-c:v h264 -b:v 300k -vf scale=-2:360 -g 50 \
-c:a aac -b:a 80k \
-f hls \
-hls_init_time 0 -hls_time 2 \
-hls_list_size 120 -hls_flags delete_segments \
-hls_segment_type fmp4 \
stream/stream.m3u8
```

[hwaccel]: https://trac.ffmpeg.org/wiki/HWAccelIntro
[plaintext]: https://gitler.moe/ninya9k/anonstream/raw/branch/master/doc/guide/OBS.md
