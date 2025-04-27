import os
import json
import subprocess
import logging
import requests
from flask import Flask, Response, request
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from io import BytesIO

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

CHANNELS = {
    "dhruvrathee": "https://youtube.com/@dhruvrathee/videos",
    "studyiq": "https://youtube.com/@studyiqiasenglish/videos",
    "karikku": "https://youtube.com/@karikku_fresh/videos",
    # Add more channels here
}

def fetch_latest_video_info(channel_url):
    try:
        result = subprocess.run([
            "yt-dlp",
            "--dump-single-json",
            "--playlist-end", "1",
            "--user-agent", FIXED_USER_AGENT,
            channel_url
        ], capture_output=True, text=True, check=True)

        data = json.loads(result.stdout)
        video = data["entries"][0]
        return f"https://www.youtube.com/watch?v={video['id']}", video.get("thumbnail", "")
    except Exception as e:
        logging.error(f"Error fetching video info: {e}")
        return None, None

def download_audio(video_url, filename):
    try:
        subprocess.run([
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "--output", str(filename),
            "--user-agent", FIXED_USER_AGENT,
            video_url
        ], check=True)
        return filename
    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        return None

def embed_thumbnail(mp3_path, thumbnail_url):
    try:
        img_data = requests.get(thumbnail_url).content
        audio = MP3(mp3_path, ID3=ID3)
        try:
            audio.add_tags()
        except error:
            pass
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=img_data
            )
        )
        audio.save()
        logging.info(f"Embedded thumbnail into {mp3_path}")
    except Exception as e:
        logging.error(f"Failed to embed thumbnail: {e}")

@app.route("/<channel>.mp3")
def stream_mp3(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    video_url, thumbnail_url = fetch_latest_video_info(CHANNELS[channel])
    if not video_url:
        return "Failed to fetch video", 500

    tmp_mp3 = TMP_DIR / f"{channel}.mp3"
    if tmp_mp3.exists():
        tmp_mp3.unlink()

    mp3_file = download_audio(video_url, tmp_mp3)
    if not mp3_file:
        return "Failed to download audio", 500

    if thumbnail_url:
        embed_thumbnail(mp3_file, thumbnail_url)

    def generate():
        with open(mp3_file, 'rb') as f:
            while chunk := f.read(4096):
                yield chunk
        try:
            tmp_mp3.unlink()
        except:
            pass

    return Response(generate(), mimetype="audio/mpeg")

@app.route("/thumb/<channel>.jpg")
def thumb(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    _, thumbnail_url = fetch_latest_video_info(CHANNELS[channel])
    if not thumbnail_url:
        thumbnail_url = "https://via.placeholder.com/320x180?text=No+Thumbnail"

    try:
        r = requests.get(thumbnail_url, headers={"User-Agent": FIXED_USER_AGENT})
        return Response(r.content, mimetype="image/jpeg")
    except:
        return "Failed to fetch thumbnail", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)