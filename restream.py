from flask import Flask, Response, request, jsonify
import subprocess
import json
import os
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 🔐 Optional token protection (set ACCESS_TOKEN in env to enable)
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", None)

# 🎯 Target YouTube channel
STATION_NAME = "safari_tv"
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@safaritvlive/videos"

@app.before_request
def require_token():
    if ACCESS_TOKEN:
        token = request.args.get("token")
        if token != ACCESS_TOKEN:
            return "Unauthorized", 403

def get_latest_video_url():
    try:
        cmd = f"yt-dlp --flat-playlist --playlist-end 1 --dump-json {YOUTUBE_CHANNEL_URL}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode != 0 or not result.stdout.strip():
            logging.error(f"yt-dlp failed: {result.stderr}")
            return None

        data = json.loads(result.stdout.strip())
        video_id = data.get("id")
        if not video_id:
            logging.error("No video ID found.")
            return None

        return f"https://www.youtube.com/watch?v={video_id}"

    except Exception as e:
        logging.exception("Failed to get latest video URL")
        return None

@app.route("/stream.mp3")
def stream_mp3():
    video_url = get_latest_video_url()
    if not video_url:
        return "Unable to fetch video URL", 503

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
            for chunk in iter(lambda: ffmpeg.stdout.read(4096), b""):
                yield chunk
        finally:
            ytdlp.kill()
            ffmpeg.kill()

    return Response(generate(), mimetype="audio/mpeg")

@app.route("/stations")
def list_stations():
    return jsonify({ "stations": [STATION_NAME] })

@app.route("/safari_tv.m3u")
def safari_tv_m3u():
    host = request.host
    token_param = f"?token={ACCESS_TOKEN}" if ACCESS_TOKEN else ""
    return Response(
        f"#EXTM3U\n#EXTINF:-1,Safari TV\nhttp://{host}/stream.mp3{token_param}",
        mimetype="audio/x-mpegurl"
    )

@app.route("/health")
def health():
    return "OK", 200

@app.route("/")
def index():
    return f'''
        <h2>Safari TV MP3 Stream</h2>
        <ul>
            <li><a href="/stream.mp3">▶️ Play Stream</a></li>
            <li><a href="/safari_tv.m3u">📄 Download M3U</a></li>
            <li><a href="/stations">📡 View Stations</a></li>
            <li><a href="/health">💓 Health Check</a></li>
        </ul>
    '''

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
