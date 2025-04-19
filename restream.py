from flask import Flask, Response
import subprocess
import json
import os
import logging
import time
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# List of YouTube channels to fetch from
CHANNELS = {
    "babu": "https://www.youtube.com/@babu_ramachandran/videos",
    "ddm": "https://www.youtube.com/@ddmalayalamtv/videos",
    "furqan": "https://www.youtube.com/@alfurqan4991/videos",
    "skicr": "https://www.youtube.com/@skicrtv/videos",
    "dhruvrathee": "https://youtube.com/@dhruvrathee",
    "safaritvlive": "https://youtube.com/@safaritvlive?si=l-aMjrXgt_7wsWT_",
    "sunnahdebate1438": "https://youtube.com/@sunnahdebate1438?si=pK57iZt9LbYnVFxp",
    "sunnxtmalayalam": "https://youtube.com/@sunnxtmalayalam?si=IXlzA4ImiZY4i2tl",
    "movieworldmalayalammovies": "https://youtube.com/@movieworldmalayalammovies?si=AgajbLBunHCvbOJp",
    "malayalamcomedyscene5334": "https://youtube.com/@malayalamcomedyscene5334?si=jN4rz7xGAx9vP1Gj",
}

# Cache to store the current video URL and stream URL
VIDEO_CACHE = {name: {"url": None, "stream_url": None, "last_checked": 0} for name in CHANNELS}

# Fetch the latest video URL from a channel
def fetch_latest_video_url(channel_url):
    try:
        cmd = [
            "yt-dlp", "--flat-playlist", "--playlist-end", "1",
            "--dump-single-json", "--cookies", "/mnt/data/cookies.txt", channel_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("yt-dlp error: %s", result.stderr)
            return None

        data = json.loads(result.stdout)
        video_id = data["entries"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        logging.exception("Error fetching latest video URL")
        return None

# Get the best audio URL for a video
def get_best_audio_url(video_url):
    try:
        cmd = [
            "yt-dlp", "-f", "233", "-g", "--cookies", "/mnt/data/cookies.txt", video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logging.error("yt-dlp error: %s", result.stderr)
            return None
    except Exception:
        logging.exception("Error extracting best audio URL")
        return None

# Loop to periodically update the video cache
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            logging.info(f"Refreshing for {name}...")
            video_url = fetch_latest_video_url(url)
            if video_url:
                stream_url = get_best_audio_url(video_url)
                if stream_url:
                    VIDEO_CACHE[name]["url"] = video_url
                    VIDEO_CACHE[name]["stream_url"] = stream_url
                    VIDEO_CACHE[name]["last_checked"] = time.time()
                    logging.info(f"✅ {name}: {video_url} -> {stream_url}")
                else:
                    logging.warning(f"❌ Could not get stream URL for {name}")
            else:
                logging.warning(f"❌ Could not fetch video URL for {name}")
        time.sleep(1800)  # Wait 30 minutes before checking again

# Start the cache update thread
threading.Thread(target=update_video_cache_loop, daemon=True).start()

# Generate the stream for the given audio URL
def generate_stream(url):
    while True:
        process = subprocess.Popen([
    "ffmpeg", "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10",
    "-user_agent", "Mozilla/5.0",
    "-i", url,
    "-vn",             # no video
    "-ac", "1",        # mono audio
    "-b:a", "40k",     # audio bitrate
    "-bufsize", "1M",  # buffer size
    "-f", "mp3",       # output format
    "-"
], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                yield chunk
                time.sleep(0.02)
        except GeneratorExit:
            process.terminate()
            process.wait()
            break
        except Exception:
            process.terminate()
            process.wait()
            time.sleep(5)

# Flask route to stream audio for a specific channel
@app.route("/<channel>.mp3")
def stream_mp3(channel):
    data = VIDEO_CACHE.get(channel)
    if not data or not data.get("stream_url"):
        return f"Stream for '{channel}' not ready", 503
    return Response(generate_stream(data["stream_url"]), mimetype="audio/mpeg")

# Home route to list available streams
@app.route("/")
def index():
    links = [f'<li><a href="/{ch}.mp3">{ch}.mp3</a></li>' for ch in CHANNELS]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

# Start the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)