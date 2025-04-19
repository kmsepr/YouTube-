from flask import Flask, Response
import subprocess
import json
import os
import logging
import time
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# List of YouTube channels to fetch from
CHANNELS = {
    "vallathorukatha": "https://www.youtube.com/@babu_ramachandran/videos",
    "furqan": "https://youtube.com/@alfurqan4991/videos",
    "skicr": "https://youtube.com/@skicrtv/videos",
    "dhruvrathee": "https://youtube.com/@dhruvrathee/videos",
    "safari": "https://youtube.com/@safaritvlive/videos",
    "sunnahdebate": "https://youtube.com/@sunnahdebate1438/videos",
    "sunnxt": "https://youtube.com/@sunnxtmalayalam/videos",
    "movieworld": "https://youtube.com/@movieworldmalayalammovies/videos",
    "comedy": "https://youtube.com/@malayalamcomedyscene5334/videos",
    "studyiq": "https://youtube.com/@studyiqiasenglish/videos",
    "vijayakumarblathur": "https://youtube.com/@vijayakumarblathur/videos",
}

# Cache to store the current video URL and stream URL
VIDEO_CACHE = {name: {"url": None, "stream_url": None, "last_checked": 0} for name in CHANNELS}

# Fetch the latest video URL from a channel
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

# Get the best audio URL for a video
def get_best_audio_url(video_url):
    try:
        cmd = [
            "yt-dlp", "-f", "bestaudio", "-g", "--cookies", "/mnt/data/cookies.txt", video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logging.error("yt-dlp error: %s", result.stderr)
            return None
    except Exception:
        logging.exception("Error extracting best audio URL")
        return None

# Loop to periodically update the video cache
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            logging.info(f"Refreshing for {name}...")
            video_url = fetch_latest_video_url(url)
            if video_url:
                stream_url = get_best_audio_url(video_url)
                if stream_url:
                    VIDEO_CACHE[name]["url"] = video_url
                    VIDEO_CACHE[name]["stream_url"] = stream_url
                    VIDEO_CACHE[name]["last_checked"] = time.time()
                    logging.info(f"✅ {name}: {video_url} -> {stream_url}")
                else:
                    logging.warning(f"❌ Could not get stream URL for {name}")
            else:
                logging.warning(f"❌ Could not fetch video URL for {name}")
        time.sleep(1800)  # Wait 30 minutes before checking again

# Start the cache update thread
threading.Thread(target=update_video_cache_loop, daemon=True).start()

# Generate the stream for the given file path
def generate_stream(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(4096)  # Adjust chunk size if necessary
            while chunk:
                yield chunk
                chunk = f.read(4096)  # Read next chunk
                time.sleep(0.02)  # Prevent buffer overrun
    except Exception as e:
        logging.error(f"Error streaming file: {e}")

# Flask route to stream audio for a specific channel
@app.route("/<channel>.mp3")
def stream_mp3(channel):
    data = VIDEO_CACHE.get(channel)
    if not data or not data.get("stream_url"):
        return f"Stream for '{channel}' not ready", 503

    # Create temporary MP3 file for streaming
    temp_file = f"/tmp/{channel}.mp3"
    
    # Convert the video to MP3 and store in the temp file
    try:
        cmd = [
            "yt-dlp", "-f", "bestaudio", "-o", temp_file,
            "--cookies", "/mnt/data/cookies.txt", data["url"]
        ]
        subprocess.run(cmd, check=True)

        # Stream the MP3 file
        return Response(generate_stream(temp_file), mimetype="audio/mpeg")

    except Exception as e:
        logging.error(f"Error generating or streaming MP3 for {channel}: {e}")
        return f"Error generating stream for {channel}", 500

    finally:
        # Cleanup the temporary file after streaming
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Home route to list available streams
@app.route("/")
def index():
    links = [f'<li><a href="/{ch}.mp3">{ch}.mp3</a></li>' for ch in CHANNELS]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

# Start the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)