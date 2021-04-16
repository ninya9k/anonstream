const t0 = Date.now() / 1000;
const playbackTimeout = 20.0; // seconds until playback should have begun

const segmentDuration = 8.0; // seconds per segment
const latencyThreshold = 180; // notify the viewer once they cross this threshold
const segmentThreshold = latencyThreshold / segmentDuration;

const heartbeatPeriod = 20.0; // seconds between heartbeats

const video = document.querySelector("video");
const videojsEnabled = parseInt(document.getElementById("videojs-enabled").value);
let firstSegment;

if ( !videojsEnabled ) {
    firstSegment = parseInt(/segment=(\d+)/.exec(video.src)[1]);
}

let token, streamTitle, viewerCount, streamStatus, streamLight, refreshButton, radialLoader;
let streamAbsoluteStart, streamRelativeStart, streamTimer, streamTimerLastUpdated;

// ensure only one heartbeat is sent at a time
let heartIsBeating = false;

let nextHeartbeat;

let streamInfoFrame = window.frames["stream-info"];
streamInfoFrame.addEventListener("load", function() {
    console.log("stream info iframe loaded");

    const streamInfo = streamInfoFrame.contentDocument
    streamTitle = streamInfo.getElementById("stream-title");
    viewerCount = streamInfo.getElementById("viewer-count");

    streamStatus = streamInfo.getElementById("stream-status");
    streamLight = streamInfo.getElementById("stream-light");
    refreshStreamButton = streamInfo.getElementById("refresh-stream-button");
    refreshPageButton = streamInfo.getElementById("refresh-page-button");

    refreshStreamButton.onclick = function() { refreshStreamButton.style.display = "none"; return video.load(); };
    refreshPageButton.onclick   = function() { return window.location.reload(true); };

    streamTimer = streamInfo.getElementById("uptime");
    streamAbsoluteStart = streamInfoFrame.contentWindow.streamAbsoluteStart;
    streamRelativeStart = streamInfoFrame.contentWindow.streamRelativeStart;
    streamTimerLastUpdated = Date.now() / 1000;

    radialLoader = streamInfo.getElementById("radial-loader");

    // this viewer's token
    token = document.getElementById("token").value;

    // get stream info every heartbeatPeriod seconds
    setInterval(heartbeat, heartbeatPeriod * 1000);

    // update stream timer every second
    setInterval(updateStreamTimer, 1000);
});

function currentSegment() {
    if ( videojsEnabled ) {
        try {
            let player = videojs.players.vjs_video_3;
            if ( player == null ) {
                player = videojs.players.videojs;
            }
            const tracks = player.textTracks();
            const cues = tracks[0].cues;
            const uri = cues[cues.length - 1].value.uri;
            return parseInt(uri.split("/")[3].slice(6));
        } catch ( error ) {
            return null;
        }
    } else {
        if ( video.readyState != video.HAVE_ENOUGH_DATA || video.networkState == video.NETWORK_IDLE ) {
            return null;
        }
        return firstSegment + Math.floor(video.duration / segmentDuration);
    }
}

function updateStreamStatus(msg, backgroundColor, refreshStream, refreshPage) {
    // TODO: figure out why when the colour is yellow the stream light moves down a few pixels
    streamStatus.innerHTML = msg;
    streamLight.style.backgroundColor = backgroundColor;

    // doesn't work with videojs: there are errors in the console; probably there is a workaround
    // could work with html5 video but we'd need to find what segment to start at; too complicated for now
    refreshPage = refreshPage | refreshStream;
    refreshStream = false;

    if ( refreshStream ) {
        refreshStreamButton.style.display = null;
    } else {
        refreshStreamButton.style.display = "none";
    }
    if ( refreshPage ) {
        refreshPageButton.style.display = null;
    } else {
        refreshPageButton.style.display = "none";
    }
}

function updateStreamTimer() {
    if ( streamTimer == null ) {
        return;
    }
    let diff = streamRelativeStart;
    if ( !Number.isInteger(diff) ) {
        streamTimer.innerHTML = "";
    } else {
        diff += Math.floor(Date.now() / 1000 - streamTimerLastUpdated);

        const hours = Math.floor(diff / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        const seconds = diff % 60;

        const mm = ("0" + minutes).slice(-2);
        const ss = ("0" + seconds).slice(-2);

        if ( hours == 0 ) {
            streamTimer.innerHTML = `${mm}:${ss}`;
        } else if ( hours < 1000 ) {
            streamTimer.innerHTML = `${hours}:${mm}:${ss}`;
        } else {
            streamTimer.innerHTML = "1000+ hours";
        }
    }
}

function resetRadialLoader(animationDuration) {
    const element = radialLoader;
    const newElement = element.cloneNode(true);
    newElement.children[0].style.animationDuration = animationDuration + "s";
    element.parentNode.replaceChild(newElement, element);
    radialLoader = newElement;
}

// TODO: this
function fitFrame(frame) {
}

// get stream info from the server (viewer count, current segment, if stream is online, etc.)
function heartbeat() {
    nextHeartbeat = Date.now() / 1000 + heartbeatPeriod;

    if ( heartIsBeating ) {
        return;
    } else {
        heartIsBeating = true;
    }

    try {
        // prepare a request to /heartbeat
        const xhr = new XMLHttpRequest();
        xhr.open("GET", `/heartbeat?token=${token}`);

        xhr.timeout = 18000; // timeout in ms, 18 seconds
        xhr.onerror = function(e) {
            heartIsBeating = false;
            console.log(e);
            updateStreamStatus("The stream was unreachable. Try refreshing the page.", "yellow", false, true);
        }
        xhr.ontimeout = xhr.onerror;
        xhr.onload = function(e) {
            heartIsBeating = false;
            if ( xhr.status != 200 ) {
                return xhr.onerror(xhr);
            }
            response = JSON.parse(xhr.responseText)

            // reset radial loader
            resetRadialLoader(nextHeartbeat - Date.now() / 1000);

            // update viewer count
            viewerCount.innerHTML = response.viewers;

            // update stream title
            streamTitle.innerHTML = response.title;

            // update stream start time (for the timer)
            const oldStreamAbsoluteStart = streamAbsoluteStart;
            streamAbsoluteStart = response.start_abs;
            streamRelativeStart = response.start_rel;
            streamTimerLastUpdated = Date.now() / 1000;

            // update stream status
            if ( !response.online ) {
                return updateStreamStatus("The stream has ended.", "red", false, false);
            }

           const serverSegment = response.current_segment;
            if ( !Number.isInteger(serverSegment) ) {
                return updateStreamStatus("The stream restarted. Reload the stream.", "yellow", true, false);
            }

            if ( oldStreamAbsoluteStart != response.start_abs ) {
                return updateStreamStatus("The stream restarted. Reload the stream.", "yellow", true, false);
            }

            // when the page is first loaded clientSegment may be null
            const clientSegment = currentSegment();
            if ( Number.isInteger(clientSegment) ) {
                const diff = serverSegment - clientSegment;
                if ( diff >= segmentThreshold ) {
                    return updateStreamStatus(`You're more than ${latencyThreshold} seconds behind the stream. Reload the stream.`, "yellow", true, false);
                } else if ( diff < 0 ) {
                    return updateStreamStatus("The stream restarted. Reload the stream.", "yellow", true, false);
                }
            } else if (Date.now() / 1000 - t0 >= playbackTimeout) {
                return updateStreamStatus("The stream is online but you're not receiving it. Try refreshing the page.", "yellow", false, true);
            }

            // otherwise
            return updateStreamStatus("The stream is online.", "green", false, false);
        }

        xhr.send();
    } catch ( error ) {
        heartIsBeating = false;
        throw error;
    }
}
