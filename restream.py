from flask import Flask, Response
import subprocess
import json
import os

app = Flask(__name__)
YOUTUBE_URL = "https://www.youtube.com/@safaritvlive/videos"

def get_latest_video_url():
    cmd = f"yt-dlp --flat-playlist --playlist-end 1 --dump-json {YOUTUBE_URL}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    data = json.loads(result.stdout.strip())  # Fix: parse the JSON correctly
    video_id = data['id']
    return f"https://www.youtube.com/watch?v={video_id}"

@app.route("/stream.mp3")
def stream_mp3():
    video_url = get_latest_video_url()
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
    return '<h2>Safari TV MP3 Stream</h2><a href="/stream.mp3">Play Stream</a>'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Get Koyeb's port environment variable
    app.run(host="0.0.0.0", port=port)
