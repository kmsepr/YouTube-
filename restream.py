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
    "dhruvrathee": "https://youtube.com/@dhruvrathee/videos",
    "safari": "https://youtube.com/@safaritvlive/videos",
    "sunnahdebate": "https://youtube.com/@sunnahdebate1438/videos",
    "sunnxt": "https://youtube.com/@sunnxtmalayalam/videos",
    "movieworld": "https://youtube.com/@movieworldmalayalammovies/videos",
    "comedy": "https://youtube.com/@malayalamcomedyscene5334/videos",
    "studyiq": "https://youtube.com/@studyiqiasenglish/videos",
}

# Cache to store the current video ID (not stream URL)
VIDEO_CACHE = {name: {"url": None, "last_checked": 0} for name in CHANNELS}

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

# Get a fresh best audio URL (used directly in stream)
def get_best_audio_url(video_url):
    try:
        cmd = [
            "yt-dlp", "-f", "bestaudio", "-g", "--cookies", "/mnt/data/cookies.txt", video_url
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

# Background thread to update video URLs every 3 hours
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            logging.info(f"Refreshing for {name}...")
            video_url = fetch_latest_video_url(url)
            if video_url:
                VIDEO_CACHE[name]["url"] = video_url
                VIDEO_CACHE[name]["last_checked"] = time.time()
                logging.info(f"✅ {name}: {video_url}")
            else:
                logging.warning(f"❌ Could not fetch video URL for {name}")
        time.sleep(10800)  # 3 hours

# Start background thread
threading.Thread(target=update_video_cache_loop, daemon=True).start()

# Stream generator using FFmpeg
def generate_stream(url):
    while True:
        process = subprocess.Popen([
            "ffmpeg", "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10",
            "-user_agent", "Mozilla/5.0",
            "-i", url,
            "-vn", "-ac", "1", "-b:a", "40k", "-bufsize", "1M", "-f", "mp3", "-"
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

# Route to stream audio for a specific channel
@app.route("/<channel>.mp3")
def stream_mp3(channel):
    data = VIDEO_CACHE.get(channel)
    if not data or not data.get("url"):
        return f"Stream for '{channel}' not ready", 503

    # Get fresh stream URL for this playback
    stream_url = get_best_audio_url(data["url"])
    if not stream_url:
        return "Failed to get stream URL", 503

    return Response(generate_stream(stream_url), mimetype="audio/mpeg")

# Home route listing available channels
@app.route("/")
def index():
    links = [f'<li><a href="/{ch}.mp3">{ch}.mp3</a></li>' for ch in CHANNELS]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

# Start the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)