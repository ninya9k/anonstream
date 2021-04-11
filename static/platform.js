const t0 = Date.now() / 1000;
const beginTimeout = 20.0; // seconds until playback should have begun

const segmentDuration = 10.0; // seconds per segment
const latencyThreshold = 180; // notify the viewer once they cross this threshold
const segmentThreshold = latencyThreshold / segmentDuration;

let token, streamTitle, viewerCount, streamStatus, streamLight, refreshButton

// ensure only one heartbeat is sent at a time
let heartIsBeating = false;

/*// https://github.com/30-seconds/30-seconds-of-code/blob/master/snippets/parseCookie.md
const parseCookie = str =>
  str
    .split(';')
    .map(v => v.split('='))
    .reduce((acc, v) => {
      acc[decodeURIComponent(v[0].trim())] = decodeURIComponent(v[1].trim());
      return acc;
    }, {});*/

let streamInfoFrame = window.frames['stream-info'];
streamInfoFrame.addEventListener("load", function() {
    console.log("stream info iframe loaded");

    const streamInfo = streamInfoFrame.contentDocument
    streamTitle = streamInfo.getElementById("stream-title");
    viewerCount = streamInfo.getElementById("viewer-count");

    streamStatus = streamInfo.getElementById("stream-status");
    streamLight = streamInfo.getElementById("stream-light");
    refreshButton = streamInfo.getElementById("refresh-button");

    refreshButton.onclick = function() { return window.location.reload(true); };

    // this viewer's token
    token = document.getElementById("token").value;

    // get stream info every 20 seconds
    setInterval(heartbeat, 20000);
});

function currentSegment() {
    try {
        const tracks = videojs.players.vjs_video_3.textTracks();
        const cues = tracks[0].cues;
        const uri = cues[cues.length - 1].value.uri;
        return parseInt(uri.split("/")[3].slice(6));
    } catch ( error ) {
        return null;
    }
}

function updateStreamStatus(msg, color, showRefreshButton) {
    streamStatus.innerHTML = msg;
    streamLight.style.color = color;
    if ( showRefreshButton ) {
        refreshButton.style.display = "";
    } else {
        refreshButton.style.display = "none";
    }
}

// get stream info from the server (viewer count, current segment, if stream is online)
function heartbeat() {
    if ( heartIsBeating ) {
        return;
    } else {
        heartIsBeating = true;
    }

    // prepare a request to /heartbeat
    const xhr = new XMLHttpRequest();
    xhr.open("GET", `/heartbeat?token=${token}`);

    xhr.timeout = 18000; // timeout in ms, 18 seconds
    xhr.onerror = function(e) {
        heartIsBeating = false;
        console.log(e);
        updateStreamStatus("The stream was unreachable. Try refreshing the page.", "yellow", true);
    }
    xhr.ontimeout = xhr.onerror;
    xhr.onload = function(e) {
        heartIsBeating = false;
        if ( xhr.status != 200 ) {
            return xhr.onerror(xhr);
        }
        response = JSON.parse(xhr.responseText)

        // update viewer count
        viewerCount.innerHTML = response.viewers;

        // update stream title
        streamTitle.innerHTML = response.title;

        // update stream status
        if ( !response.online ) {
            return updateStreamStatus("The stream has ended.", "red", false);
        }

        const serverSegment = response.current_segment;
        if ( !Number.isInteger(serverSegment) ) {
            return updateStreamStatus("The stream has ended.", "red", false);
        }

        // when the page is first loaded clientSegment may be null
        const clientSegment = currentSegment();
        if ( Number.isInteger(clientSegment) ) {
            const diff = serverSegment - clientSegment;
            if ( diff >= segmentThreshold ) {
                return updateStreamStatus(`You're more than ${latencyThreshold} seconds behind the stream. Refresh the page.`, "yellow", true);
            } else if ( diff < 0 ) {
                return updateStreamStatus("The stream restarted. Refresh the page.", "yellow", true);
            }
        } else if (Date.now() / 1000 - t0 >= beginTimeout) {
            updateStreamStatus("The stream was unreachable. Try refreshing the page.", "yellow", true);
        }

        // otherwise
        return updateStreamStatus("The stream is online.", "green", false);
    }

    xhr.send();
}
