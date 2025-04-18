from flask import Flask, Response
import subprocess
import json
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

YOUTUBE_URL = "https://youtube.com/playlist?list=PLLSiSzpILVXmTXgDdM1FXNZVyTz_Nca52"

def get_latest_video_url():
    cmd = f"yt-dlp --flat-playlist --playlist-end 1 --dump-json {YOUTUBE_URL}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        logging.error(f"Error fetching video data: {result.stderr}")
        return None

    try:
        data = json.loads(result.stdout.strip())
        if isinstance(data, list) and data:
            video_id = data[0]['id']
            return f"https://www.youtube.com/watch?v={video_id}"
        else:
            logging.error("No video found in the playlist.")
            return None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON: {e}")
        return None

@app.route("/stream.mp3")
def stream_mp3():
    video_url = get_latest_video_url()
    
    if not video_url:
        return "Unable to fetch the latest video URL.", 500

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

    try:
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
    
    except Exception as e:
        logging.error(f"Error during stream processing: {e}")
        return "Error while streaming the audio.", 500

@app.route("/")
def index():
    return '<h2>Safari TV MP3 Stream</h2><a href="/stream.mp3">Play Stream</a>'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Get Koyeb's port environment variable
    app.run(host="0.0.0.0", port=port)
