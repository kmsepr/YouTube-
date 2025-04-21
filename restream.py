# Imports (same as before)
from flask import Flask, Response, request
import subprocess, json, os, logging, time, threading, random
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Constants (unchanged)
REFRESH_INTERVAL = 900
RECHECK_INTERVAL = 1800
CLEANUP_INTERVAL = 1800
EXPIRE_AGE = 10800

# Channels list (same as your original)
CHANNELS = {
    "qasimi": "https://www.youtube.com/@quranstudycentremukkam/videos",
    "sharique": "https://www.youtube.com/@shariquesamsudheen/videos",
    # ... other channels ...
}

VIDEO_CACHE = {name: {"url": None, "last_checked": 0} for name in CHANNELS}
TMP_DIR = Path("/tmp/ytvid")
TMP_DIR.mkdir(exist_ok=True)

# Cleanup old files
def cleanup_old_files():
    while True:
        now = time.time()
        for f in TMP_DIR.glob("*.mp4"):
            if now - f.stat().st_mtime > EXPIRE_AGE:
                try:
                    f.unlink()
                    logging.info(f"Deleted old file: {f}")
                except Exception as e:
                    logging.warning(f"Could not delete {f}: {e}")
        time.sleep(CLEANUP_INTERVAL)

# Update video cache loop
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            video_url = fetch_latest_video_url(url)
            if video_url:
                VIDEO_CACHE[name]["url"] = video_url
                VIDEO_CACHE[name]["last_checked"] = time.time()
                download_and_convert(name, video_url)
            time.sleep(random.randint(5, 10))
        time.sleep(REFRESH_INTERVAL)

# Periodic downloader
def auto_download_videos():
    while True:
        for name, data in VIDEO_CACHE.items():
            video_url = data.get("url")
            if video_url:
                mp4_path = TMP_DIR / f"{name}.mp4"
                if not mp4_path.exists() or time.time() - mp4_path.stat().st_mtime > RECHECK_INTERVAL:
                    logging.info(f"Pre-downloading {name}")
                    download_and_convert(name, video_url)
            time.sleep(random.randint(5, 10))
        time.sleep(RECHECK_INTERVAL)

def fetch_latest_video_url(channel_url):
    try:
        result = subprocess.run([
            "yt-dlp", "--flat-playlist", "--playlist-end", "1",
            "--dump-single-json", "--cookies", "/mnt/data/cookies.txt", channel_url
        ], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_id = data["entries"][0]["id"]
        time.sleep(random.randint(5, 10))
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        logging.error(f"Error fetching video from {channel_url}: {e}")
        return None

def download_and_convert(channel, video_url):
    mp4_path = TMP_DIR / f"{channel}.mp4"
    webm_path = TMP_DIR / f"{channel}.webm"

    if mp4_path.exists():
        return mp4_path

    try:
        subprocess.run([
            "yt-dlp", "-f", "bestvideo[ext=webm]+bestaudio[ext=webm]/best",
            "--output", str(webm_path),
            "--cookies", "/mnt/data/cookies.txt",
            video_url
        ], check=True)

        subprocess.run([
            "ffmpeg", "-y", "-i", str(webm_path),
            "-vf", "scale=320:240", "-r", "15",
            "-b:v", "384k", "-b:a", "12k", "-ac", "1",
            "-c:v", "libx264", "-c:a", "aac",
            str(mp4_path)
        ], check=True)

        if webm_path.exists():
            webm_path.unlink()

        return mp4_path if mp4_path.exists() else None

    except Exception as e:
        logging.error(f"Error converting {channel}: {e}")
        return None

@app.route("/<channel>.mp4")
def stream_video(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    video_url = VIDEO_CACHE[channel].get("url") or fetch_latest_video_url(CHANNELS[channel])
    if not video_url:
        return "Unable to fetch video", 500

    VIDEO_CACHE[channel]["url"] = video_url
    VIDEO_CACHE[channel]["last_checked"] = time.time()

    mp4_path = download_and_convert(channel, video_url)
    if not mp4_path or not mp4_path.exists():
        return "Error preparing video", 500

    file_size = os.path.getsize(mp4_path)
    range_header = request.headers.get('Range', None)
    headers = {
        'Content-Type': 'video/mp4',
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
        with open(mp4_path, 'rb') as f:
            f.seek(byte1)
            chunk = f.read(length)

        headers.update({
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Content-Length': str(length)
        })

        return Response(chunk, status=206, headers=headers)

    with open(mp4_path, 'rb') as f:
        data = f.read()
    headers['Content-Length'] = str(file_size)
    return Response(data, headers=headers)

@app.route("/")
def index():
    files = list(TMP_DIR.glob("*.mp4"))
    links = [f'<li><a href="/{f.stem}.mp4">{f.stem}.mp4</a> (created: {time.ctime(f.stat().st_mtime)})</li>' for f in files]
    return f"<h3>Available Video Streams</h3><ul>{''.join(links)}</ul>"

# Start background threads
threading.Thread(target=update_video_cache_loop, daemon=True).start()
threading.Thread(target=cleanup_old_files, daemon=True).start()
threading.Thread(target=auto_download_videos, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)