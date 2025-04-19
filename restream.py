import os
import subprocess
import time
import threading
from flask import Flask, Response
import logging
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Path to persistent storage (adjust based on your Koyeb setup)
CACHE_DIR = "/mnt/data/audio_cache"  # Koyeb persistent storage
os.makedirs(CACHE_DIR, exist_ok=True)

# List of YouTube channels to fetch from
CHANNELS = {
    "babu": "https://www.youtube.com/@babu_ramachandran/videos",
    "ddm": "https://www.youtube.com/@ddmalayalamtv/videos",
    "furqan": "https://www.youtube.com/@alfurqan4991/videos",
    # Add more channels...
}

# Cache to store video URLs and file paths
VIDEO_CACHE = {name: {"url": None, "file": None, "last_checked": 0} for name in CHANNELS}

# Function to fetch the latest video URL from YouTube
def fetch_latest_video_url(channel_url):
    try:
        cmd = [
            "yt-dlp", "--flat-playlist", "--playlist-end", "1",
            "--dump-single-json", "--cookies", "/mnt/data/cookies.txt", channel_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("yt-dlp error: %s", result.stderr)
            return None

        data = json.loads(result.stdout)
        video_id = data["entries"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        logging.exception("Error fetching latest video URL")
        return None

# Function to download the audio for the latest video
def download_audio(video_url, channel_name):
    audio_path = os.path.join(CACHE_DIR, f"{channel_name}.mp3")
    if not os.path.exists(audio_path):  # Download if file doesn't exist
        logging.info(f"Downloading audio for {channel_name}...")
        cmd = [
            "yt-dlp", "-f", "bestaudio", "--output", audio_path,
            "--cookies", "/mnt/data/cookies.txt", video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(f"Error downloading audio for {channel_name}: {result.stderr}")
            return None
        logging.info(f"Downloaded audio for {channel_name} to {audio_path}")
    else:
        logging.info(f"Audio for {channel_name} already exists.")
    
    return audio_path

# Stream the downloaded audio
def stream_audio(audio_path):
    with open(audio_path, 'rb') as audio_file:
        while chunk := audio_file.read(4096):
            yield chunk

# Background thread to update video URLs and download audio every 3 hours
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            logging.info(f"Refreshing for {name}...")
            video_url = fetch_latest_video_url(url)
            if video_url:
                # Store the latest video URL in the cache
                VIDEO_CACHE[name]["url"] = video_url
                VIDEO_CACHE[name]["last_checked"] = time.time()
                
                # Download the audio for the latest video
                audio_path = download_audio(video_url, name)
                if audio_path:
                    VIDEO_CACHE[name]["file"] = audio_path
                    logging.info(f"✅ {name}: {audio_path}")
                else:
                    logging.warning(f"❌ Could not download audio for {name}")
            else:
                logging.warning(f"❌ Could not fetch video URL for {name}")
        
        # Wait for 3 hours (10800 seconds) before refreshing again
        time.sleep(10800)

# Start background thread for video URL refresh
threading.Thread(target=update_video_cache_loop, daemon=True).start()

# Route to stream audio for a specific channel
@app.route("/<channel>.mp3")
def stream_mp3(channel):
    data = VIDEO_CACHE.get(channel)
    if not data or not data.get("file"):
        return f"Stream for '{channel}' not ready", 503

    # Return the latest audio file for the channel
    return Response(stream_audio(data["file"]), mimetype="audio/mpeg")

# Home route listing available channels
@app.route("/")
def index():
    links = [f'<li><a href="/{ch}.mp3">{ch}.mp3</a></li>' for ch in CHANNELS]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

# Start the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)