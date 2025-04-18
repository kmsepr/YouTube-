from flask import Flask, Response
import subprocess
import json
import os
import logging
import time
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

YOUTUBE_URL = "https://www.youtube.com/@babu_ramachandran/videos"
VIDEO_CACHE = {"url": None, "last_checked": 0}

def fetch_latest_video_url():
    try:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--playlist-end", "1",
            "--dump-single-json",
            YOUTUBE_URL
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("yt-dlp error: %s", result.stderr)
            return None

        data = json.loads(result.stdout)
        if "entries" not in data or not data["entries"]:
            logging.error("No video found in playlist.")
            return None

        video_id = data["entries"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        logging.exception("Error fetching latest video URL")
        return None

def update_video_cache():
    while True:
        logging.info("Refreshing latest video URL...")
        url = fetch_latest_video_url()
        if url:
            VIDEO_CACHE["url"] = url
            VIDEO_CACHE["last_checked"] = time.time()
            logging.info(f"✅ Cached video: {url}")
        else:
            logging.warning("❌ Failed to update video cache.")
        time.sleep(1800)  # every 30 minutes

threading.Thread(target=update_video_cache, daemon=True).start()

@app.route("/stream.mp3")
def stream_mp3():
    video_url = VIDEO_CACHE.get("url")
if not video_url:
    # fallback to fetch latest
    logging.info("No cached video URL. Fetching now...")
    video_url = fetch_latest_video_url()
    if video_url:
        VIDEO_CACHE["url"] = video_url
        VIDEO_CACHE["last_checked"] = time.time()
    else:
        return "No video URL available", 503

    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--add-header", "User-Agent: Mozilla/5.0",
        "--add-header", "Accept-Language: en-US,en;q=0.5",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "-o", "-",
        video_url
    ]

    ffmpeg_cmd = [
        "ffmpeg", "-loglevel", "error", "-i", "pipe:0",
        "-vn", "-acodec", "libmp3lame",
        "-b:a", "40k", "-ac", "1",
        "-f", "mp3",
        "-fflags", "+flush_packets", "-flush_packets", "1",
        "pipe:1"
    ]

    try:
        ytdlp = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=ytdlp.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def generate():
            try:
                while True:
                    chunk = ffmpeg.stdout.read(1024)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                logging.error(f"Streaming error: {e}")
                logging.error(f"FFmpeg stderr: {ffmpeg.stderr.read().decode(errors='ignore')}")
            finally:
                ytdlp.kill()
                ffmpeg.kill()

        return Response(generate(), mimetype="audio/mpeg", headers={"Connection": "keep-alive"})

    except Exception as e:
        logging.error(f"Stream startup error: {e}")
        return "Internal server error", 500

@app.route("/")
def index():
    return '<h2>Latest YouTube Audio Stream</h2><a href="/stream.mp3">Click to listen</a>'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)