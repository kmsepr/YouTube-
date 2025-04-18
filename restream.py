from flask import Flask, Response
import subprocess
import json
import os
import logging

app = Flask(__name__)

# Logging for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 👤 Babu Ramachandran's YouTube channel
YOUTUBE_URL = "https://www.youtube.com/@babu_ramachandran/videos"

def get_latest_video_url():
    """Fetches the latest uploaded video URL."""
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
            logging.error("yt-dlp failed: %s", result.stderr)
            return None

        data = json.loads(result.stdout)
        if "entries" not in data or not data["entries"]:
            logging.error("No video found in the playlist.")
            return None

        video_id = data["entries"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        logging.exception("Failed to get latest video URL")
        return None

@app.route("/stream.mp3")
def stream_mp3():
    """Streams the latest video as MP3."""
    video_url = get_latest_video_url()
    if not video_url:
        return "No video found", 500

    ytdlp_cmd = [
        "yt-dlp",
        "--cookies", "/mnt/data/cookies.txt",
        "--add-header", "User-Agent: Mozilla/5.0",
        "--add-header", "Accept-Language: en-US,en;q=0.5",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "-o", "-",
        video_url
    ]

    ffmpeg_cmd = [
        "ffmpeg", "-i", "pipe:0",
        "-vn", "-acodec", "libmp3lame", "-f", "mp3", "pipe:1"
    ]

    ytdlp = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE)
    ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=ytdlp.stdout, stdout=subprocess.PIPE)

    def generate():
        try:
            while True:
                chunk = ffmpeg.stdout.read(1024)
                if not chunk:
                    break
                yield chunk
        finally:
            ytdlp.kill()
            ffmpeg.kill()

    return Response(generate(), mimetype="audio/mpeg")

@app.route("/")
def index():
    return '<h2>🎧 Babu Ramachandran MP3 Stream</h2><a href="/stream.mp3">▶️ Play Stream</a>'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
