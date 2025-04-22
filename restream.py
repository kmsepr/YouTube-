import os
import time
import json
import subprocess
import logging
import threading
import random
from flask import Flask, Response, request
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Constants
REFRESH_INTERVAL = 600       # Every 10 minutes
RECHECK_INTERVAL = 1200      # Every 20 minutes
CLEANUP_INTERVAL = 1800      # Every 30 minutes
EXPIRE_AGE = 7200            # Keep files for 2 hours

# User agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (Linux; Android 10; SM-G970F)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
    "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)",
]

CHANNELS = {
    "vijayakumarblathur": "https://youtube.com/@vijayakumarblathur/videos",
    "entridegree": "https://youtube.com/@entridegreelevelexams/videos",
    "maheen": "https://youtube.com/@hitchhikingnomaad/videos",
    "entri": "https://youtube.com/@entriapp/videos",
    "qasimi": "https://www.youtube.com/@quranstudycentremukkam/videos",
    "sharique": "https://www.youtube.com/@shariquesamsudheen/videos",
    "drali": "https://youtube.com/@draligomaa/videos",
    "yaqeen": "https://youtube.com/@yaqeeninstituteofficial/videos",
    "talent": "https://youtube.com/@talentacademyonline/videos",
    "suprabhatam": "https://youtube.com/@suprabhaatham2023/videos",
    "bayyinah": "https://youtube.com/@bayyinah/videos",
    "zamzam": "https://youtube.com/@zamzamacademy/videos",
    "jrstudio": "https://youtube.com/@jrstudiomalayalam/videos",
    "raftalks": "https://youtube.com/@raftalksmalayalam/videos",
    "parvinder": "https://www.youtube.com/@pravindersheoran/videos",
    "vallathorukatha": "https://www.youtube.com/@babu_ramachandran/videos",
    "furqan": "https://youtube.com/@alfurqan4991/videos",
    "skicr": "https://youtube.com/@skicrtv/videos",
    "dhruvrathee": "https://youtube.com/@dhruvrathee/videos",
    "safari": "https://youtube.com/@safaritvlive/videos",
    "sunnxt": "https://youtube.com/@sunnxtmalayalam/videos",
    "movieworld": "https://youtube.com/@movieworldmalayalammovies/videos",
    "comedy": "https://youtube.com/@malayalamcomedyscene5334/videos",
    "studyiq": "https://youtube.com/@studyiqiasenglish/videos",
}

VIDEO_CACHE = {name: {"url": None, "last_checked": 0, "thumbnail": ""} for name in CHANNELS}
LAST_VIDEO_ID = {name: None for name in CHANNELS}
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

# Functions for fetching, downloading, and cleaning up files
def cleanup_old_files():
    while True:
        now = time.time()
        for f in TMP_DIR.glob("*.mp3"):
            if now - f.stat().st_mtime > EXPIRE_AGE:
                try:
                    f.unlink()
                    logging.info(f"Deleted old file: {f}")
                except Exception as e:
                    logging.warning(f"Could not delete {f}: {e}")
        time.sleep(CLEANUP_INTERVAL)

def fetch_latest_video_url(name, channel_url):
    try:
        result = subprocess.run([
            "yt-dlp",
            "--dump-single-json",
            "--playlist-end", "1",
            "--cookies", "/mnt/data/cookies.txt",
            "--user-agent", random.choice(USER_AGENTS),
            channel_url
        ], capture_output=True, text=True, check=True)

        data = json.loads(result.stdout)
        video = data["entries"][0]
        video_id = video["id"]
        thumbnail_url = video.get("thumbnail", "")
        return f"https://www.youtube.com/watch?v={video_id}", thumbnail_url, video_id
    except Exception as e:
        logging.error(f"Error fetching video from {channel_url}: {e}")
        return None, None, None

def download_and_convert(channel, video_url):
    final_path = TMP_DIR / f"{channel}.mp3"
    if final_path.exists():
        return final_path
    if not video_url:
        return None
    try:
        subprocess.run([
            "yt-dlp",
            "-f", "bestaudio",
            "--output", str(TMP_DIR / f"{channel}.%(ext)s"),
            "--cookies", "/mnt/data/cookies.txt",
            "--user-agent", random.choice(USER_AGENTS),
            "--postprocessor-args", "-ar 22050 -ac 1 -b:a 40k",
            "--extract-audio",
            "--audio-format", "mp3",
            video_url
        ], check=True)
        return final_path if final_path.exists() else None
    except Exception as e:
        logging.error(f"Error converting {channel}: {e}")
        partial = final_path.with_suffix(".mp3.part")
        if partial.exists():
            partial.unlink()
        return None

# Background threads for automatic updates
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            video_url, thumbnail, video_id = fetch_latest_video_url(name, url)
            if video_url and video_id:
                if LAST_VIDEO_ID[name] != video_id:
                    LAST_VIDEO_ID[name] = video_id
                    VIDEO_CACHE[name]["url"] = video_url
                    VIDEO_CACHE[name]["last_checked"] = time.time()
                    VIDEO_CACHE[name]["thumbnail"] = thumbnail
                    download_and_convert(name, video_url)
            time.sleep(random.randint(5, 10))
        time.sleep(REFRESH_INTERVAL)

def auto_download_mp3s():
    while True:
        for name, data in VIDEO_CACHE.items():
            video_url = data.get("url")
            if video_url:
                mp3_path = TMP_DIR / f"{name}.mp3"
                if not mp3_path.exists() or time.time() - mp3_path.stat().st_mtime > RECHECK_INTERVAL:
                    logging.info(f"Pre-downloading {name}")
                    download_and_convert(name, video_url)
            time.sleep(random.randint(5, 10))
        time.sleep(RECHECK_INTERVAL)

# Routes
@app.route("/<channel>.mp3")
def stream_mp3(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    video_url = VIDEO_CACHE[channel].get("url")
    if not video_url:
        video_url, thumbnail, video_id = fetch_latest_video_url(channel, CHANNELS[channel])
        if not video_url:
            return "Unable to fetch video", 500
        if video_id and LAST_VIDEO_ID[channel] != video_id:
            LAST_VIDEO_ID[channel] = video_id
            VIDEO_CACHE[channel]["url"] = video_url
            VIDEO_CACHE[channel]["thumbnail"] = thumbnail
            VIDEO_CACHE[channel]["last_checked"] = time.time()

    mp3_path = download_and_convert(channel, video_url)
    if not mp3_path or not mp3_path.exists():
        return "Error preparing stream", 500

    file_size = os.path.getsize(mp3_path)
    range_header = request.headers.get('Range', None)
    headers = {
        'Content-Type': 'audio/mpeg',
        'Accept-Ranges': 'bytes',
    }

    if range_header:
        try:
            range_value = range_header.strip().split("=")[1]
            byte1, byte2 = range_value.split("-")
            byte1 = int(byte1)
            byte2 = int(byte2) if byte2 else file_size - 1
        except Exception as e:
            return f"Invalid Range header: {e}", 400

        length = byte2 - byte1 + 1
        with open(mp3_path, 'rb') as f:
            f.seek(byte1)
            chunk = f.read(length)

        headers.update({
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Content-Length': str(length)
        })
        return Response(chunk, status=206, headers=headers)

    with open(mp3_path, 'rb') as f:
        data = f.read()
    headers['Content-Length'] = str(file_size)
    return Response(data, headers=headers)

@app.route("/")
def index():
    html = """
    <html>
    <head>
        <title>Available Streams</title>
    </head>
    <body style="font-family:sans-serif; font-size:12px; background:#fff;">
        <h3>Available Streams</h3>
    """
    
    def get_mtime(channel):
        f = TMP_DIR / f"{channel}.mp3"
        return f.stat().st_mtime if f.exists() else 0

    for channel in sorted(CHANNELS, key=get_mtime, reverse=True):
        mp3_path = TMP_DIR / f"{channel}.mp3"
        if not mp3_path.exists():
            continue
        thumbnail = VIDEO_CACHE[channel].get("thumbnail", "")
        if not thumbnail:
            thumbnail = "https://via.placeholder.com/120x80?text=YT"
        
        html += f"""
        <div style="margin-bottom:12px; padding:6px; border:1px solid #ccc; border-radius:6px; width:160px;">
            <img src="{thumbnail}" loading="lazy" style="width:100%; height:auto; display:block; margin-bottom:4px;" alt="{channel}">
            <div style="text-align:center;">
                <a href="/{channel}.mp3" style="color:#000; text-decoration:none;">{channel}</a><br>
                <small>{time.ctime(mp3_path.stat().st_mtime)}</small>
            </div>
        </div>
        """

    html += "</body></html>"
    return html

# Start background threads
threading.Thread(target=update_video_cache_loop, daemon=True).start()
threading.Thread(target=cleanup_old_files, daemon=True).start()
threading.Thread(target=auto_download_mp3s, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)