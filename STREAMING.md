### Tor

Install tor and include these lines in your [torrc][torrc]:

```
HiddenServiceDir $PROJECT_ROOT/hidden_service
HiddenServicePort 80 127.0.0.1:5051
```
but replace `$PROJECT_ROOT` with the folder you cloned the git repo
into.

Then reload tor. If everything went well, the directory will have been
created and your onion address will be in
`$PROJECT_ROOT/hidden_service/hostname`.

### OBS Studio

Install OBS Studio. If the autoconfiguration wizard prompts you to
choose a third-party service, ignore it since we're not gonna be doing
that.

Click `Settings` and set these:

* Advanced
  * Recording
    * Filename Formatting: `stream`
* Video
  * Output (Scaled) Resolution: `960x540` or lower
* Output
  * Output Mode: `Advanced`
  * Recording:
    |                            |                                                                                                |
    |----------------------------|------------------------------------------------------------------------------------------------|
    | Type                       | `Custom Output (FFmpeg)`                                                                       |
    | FFmpeg Output Type         | `Output to File`                                                                               |
    | File path or URL           | same as config.toml: `segments/directory` (but should be an absolute path)                     |
    | Container Format           | `hls`                                                                                          |
    | Muxer Settings (if any)    | `hls_init_time=0 hls_time=2 hls_list_size=120 hls_flags=delete_segments hls_segment_type=fmp4` |
    | Video bitrate              | `420 Kbps` or lower                                                                            |
    | Keyframe interval (frames) | `30` (same as the framerate, or exactly half)                                                  |
    | Video Encoder              | libx264, or an H.264 hardware encoder (e.g. `h264_nvenc` for Nvidia, [see here][ffmpeg])       |
    | Audio Bitrate              | `96 Kbps`                                                                                      |
    | Audio Encoder              | `aac`                                                                                          |

Then click `OK`.

That's it. To start streaming click `Start Recording`.

Because of the muxer settings we used, segments older than four
minutes will be constantly deleted. When you stop streaming, the last
four minutes worth of segments will remain the segments directory.
You can delete them if you want. When you're not streaming you can
delete everything in the segments directory and it'll be fine.

[torrc]: https://support.torproject.org/#tbb-editing-torrc
[ffmpeg]: https://trac.ffmpeg.org/wiki/HWAccelIntro
