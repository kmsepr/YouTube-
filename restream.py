from flask import Flask, send_file, jsonify, render_template_string, request
import os
import subprocess
import threading
import time
from pathlib import Path
import yt_dlp
import requests

app = Flask(__name__)
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

CHANNELS = {
    "Malayalam": "https://www.youtube.com/@MazhavilManorama/videos",
    "Bollywood": "https://www.youtube.com/@TSeries/videos",
    "Islamic": "https://www.youtube.com/@digitalislam786/videos"
}

def fetch_latest_video_url(channel, url):
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "force_generic_extractor": False,
        "playlistend": 1,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video = info["entries"][0]
        video_id = video["id"]
        thumbnail = video.get("thumbnail")
        upload_date = video.get("upload_date", "unknown")
        return f"https://www.youtube.com/watch?v={video_id}", thumbnail, video_id, upload_date, video

def download_and_convert(channel, video_url, video=None):
    filename_base = video_url.split("v=")[-1]
    channel_cache = CACHE_DIR / channel
    channel_cache.mkdir(exist_ok=True)

    mp3_path = channel_cache / f"{filename_base}.mp3"
    if mp3_path.exists():
        return

    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": str(channel_cache / f"{filename_base}.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    audio_path = channel_cache / f"{filename_base}.mp3"
    thumb_path = channel_cache / f"{filename_base}.jpg"
    final_path = channel_cache / f"{filename_base}_final.mp3"

    if not audio_path.exists():
        return

    # Download thumbnail
    if video and video.get("thumbnail"):
        response = requests.get(video["thumbnail"])
        with open(thumb_path, "wb") as f:
            f.write(response.content)

    # Metadata fields
    title = video.get("title", channel)
    uploader = video.get("uploader", channel)
    album = video.get("channel", uploader)

    # Embed metadata and cover art
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-i", str(thumb_path),
        "-map", "0:a",
        "-map", "1:v",
        "-c:a", "libmp3lame",
        "-b:a", "40k",
        "-ar", "22050",
        "-ac", "1",
        "-id3v2_version", "3",
        "-metadata", f"title={title}",
        "-metadata", f"artist={uploader}",
        "-metadata", f"album={album}",
        "-metadata:s:v", "title=Album cover",
        "-metadata:s:v", "comment=Cover (front)",
        str(final_path)
    ], check=True)

    audio_path.unlink(missing_ok=True)
    thumb_path.unlink(missing_ok=True)

def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            try:
                video_url, thumbnail, video_id, upload_date, video = fetch_latest_video_url(name, url)
                channel_cache = CACHE_DIR / name
                final_path = channel_cache / f"{video_id}_final.mp3"
                if not final_path.exists():
                    download_and_convert(name, video_url, video)
            except Exception as e:
                print(f"Error for {name}: {e}")
        time.sleep(300)  # Refresh every 5 minutes

@app.route("/")
def index():
    html = """
    <h1>Channel Downloads</h1>
    {% for name, url in channels.items() %}
        <h2>{{ name }}</h2>
        {% set files = (cache_dir / name).glob("*_final.mp3") %}
        {% for file in files %}
            <p>
                <a href="/download/{{ name }}/{{ file.name }}">{{ file.name }}</a>
            </p>
        {% endfor %}
    {% endfor %}
    """
    return render_template_string(html, channels=CHANNELS, cache_dir=CACHE_DIR)

@app.route("/download/<channel>/<filename>")
def download(channel, filename):
    path = CACHE_DIR / channel / filename
    if not path.exists():
        return "File not found", 404
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    threading.Thread(target=update_video_cache_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)