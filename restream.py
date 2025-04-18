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
VIDEO_CACHE = {"url": None, "stream_url": None, "last_checked": 0}

def fetch_latest_video_url():
    """Fetch the latest video URL from the channel."""
    try:
        cmd = [
            "yt-dlp", "--flat-playlist", "--playlist-end", "1",
            "--dump-single-json", "--cookies", "/mnt/data/cookies.txt",
            YOUTUBE_URL
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("yt-dlp error: %s", result.stderr)
            return None

        data = json.loads(result.stdout)
        video_id = data["entries"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        logging.exception("Error fetching latest video URL")
        return None

def get_youtube_audio_url(youtube_url):
    """Extract direct stream URL."""
    try:
        command = ["/usr/local/bin/yt-dlp", "--force-generic-extractor", "-f", "91", "-g", youtube_url]
        if os.path.exists("/mnt/data/cookies.txt"):
            command.insert(2, "--cookies")
            command.insert(3, "/mnt/data/cookies.txt")

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logging.error(f"yt-dlp extraction error: {result.stderr}")
            return None
    except Exception:
        logging.exception("Exception during audio URL extraction")
        return None

def update_video_cache():
    """Update cached video and stream URL every 30 mins."""
    while True:
        logging.info("Refreshing latest video and audio URL...")
        video_url = fetch_latest_video_url()
        if video_url:
            stream_url = get_youtube_audio_url(video_url)
            if stream_url:
                VIDEO_CACHE["url"] = video_url
                VIDEO_CACHE["stream_url"] = stream_url
                VIDEO_CACHE["last_checked"] = time.time()
                logging.info(f"✅ Cached: {video_url} -> {stream_url}")
            else:
                logging.warning("❌ Could not get stream URL")
        else:
            logging.warning("❌ Could not fetch video URL")
        time.sleep(1800)  # 30 minutes

threading.Thread(target=update_video_cache, daemon=True).start()

def generate_stream(url):
    """Stream audio using FFmpeg."""
    while True:
        process = subprocess.Popen([
            "ffmpeg", "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10",
            "-user_agent", "Mozilla/5.0", "-i", url, "-vn", "-ac", "1",
            "-b:a", "40k", "-bufsize", "1M", "-f", "mp3", "-"
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

@app.route("/stream.mp3")
def stream_mp3():
    """Stream MP3 if available."""
    stream_url = VIDEO_CACHE.get("stream_url")
    if not stream_url:
        return "Stream not ready yet", 503
    return Response(generate_stream(stream_url), mimetype="audio/mpeg")

@app.route("/")
def index():
    return '<h3>Streaming Latest YouTube Video</h3><a href="/stream.mp3">Play Stream</a>'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)