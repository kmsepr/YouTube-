from flask import Flask, Response, send_file
import subprocess
import json
import os
import logging
import time
import threading
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

CHANNELS = {
    "vallathorukatha": "https://www.youtube.com/@babu_ramachandran/videos",
    "furqan": "https://youtube.com/@alfurqan4991/videos",
    "skicr": "https://youtube.com/@skicrtv/videos",
    "dhruvrathee": "https://youtube.com/@dhruvrathee/videos",
    "safari": "https://youtube.com/@safaritvlive/videos",
    "sunnahdebate": "https://youtube.com/@sunnahdebate1438/videos",
    "sunnxt": "https://youtube.com/@sunnxtmalayalam/videos",
    "movieworld": "https://youtube.com/@movieworldmalayalammovies/videos",
    "comedy": "https://youtube.com/@malayalamcomedyscene5334/videos",
    "studyiq": "https://youtube.com/@studyiqiasenglish/videos",
    "vijayakumarblathur": "https://youtube.com/@vijayakumarblathur/videos",
}

VIDEO_CACHE = {name: {"url": None, "last_checked": 0} for name in CHANNELS}
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

# Cleanup old files older than 2 hours
def cleanup_old_files():
    while True:
        now = time.time()
        for f in TMP_DIR.glob("*.mp3"):
            if now - f.stat().st_mtime > 3600:
                try:
                    f.unlink()
                    logging.info(f"Deleted old file: {f}")
                except Exception as e:
                    logging.warning(f"Could not delete {f}: {e}")
        time.sleep(1800)

# Periodic refresh of latest video URLs
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            video_url = fetch_latest_video_url(url)
            if video_url:
                VIDEO_CACHE[name]["url"] = video_url
                VIDEO_CACHE[name]["last_checked"] = time.time()
        time.sleep(1800)

def fetch_latest_video_url(channel_url):
    try:
        result = subprocess.run([
            "yt-dlp", "--flat-playlist", "--playlist-end", "1",
            "--dump-single-json", "--cookies", "/mnt/data/cookies.txt", channel_url
        ], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_id = data["entries"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        logging.error(f"Error fetching video: {e}")
        return None

def download_and_convert(channel, video_url):
    mp3_path = TMP_DIR / f"{channel}.mp3"
    if mp3_path.exists():
        return mp3_path

    try:
        audio_url = subprocess.run([
            "yt-dlp", "-f", "bestaudio", "-g", "--cookies", "/mnt/data/cookies.txt", video_url
        ], capture_output=True, text=True, check=True).stdout.strip()

        cmd = [
            "ffmpeg", "-i", audio_url,
            "-ac", "1", "-b:a", "40k", "-f", "mp3", "-y", str(mp3_path)
        ]
        subprocess.run(cmd, check=True)
        return mp3_path
    except Exception as e:
        logging.error(f"Error converting {channel}: {e}")
        return None

@app.route("/<channel>.mp3")
def stream_mp3(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    video_url = VIDEO_CACHE[channel].get("url") or fetch_latest_video_url(CHANNELS[channel])
    if not video_url:
        return "Unable to fetch video", 500

    VIDEO_CACHE[channel]["url"] = video_url
    VIDEO_CACHE[channel]["last_checked"] = time.time()

    mp3_path = download_and_convert(channel, video_url)
    if not mp3_path or not mp3_path.exists():
        return "Error preparing stream", 500

    return send_file(mp3_path, mimetype="audio/mpeg")

@app.route("/")
def index():
    files = list(TMP_DIR.glob("*.mp3"))
    links = [f'<li><a href="/{f.stem}.mp3">{f.stem}.mp3</a> (created: {time.ctime(f.stat().st_mtime)})</li>' for f in files]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

# Start background threads
threading.Thread(target=update_video_cache_loop, daemon=True).start()
threading.Thread(target=cleanup_old_files, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)