from flask import Flask, Response
import subprocess
import json
import os
import logging
import time
import threading
import tempfile

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

# Convert the video URL to MP3 and save it temporarily
def convert_to_mp3(video_url):
    try:
        # Create a temporary file for the MP3
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file.close()  # Close the file so that ffmpeg can write to it

        cmd = [
            "yt-dlp", "-f", "bestaudio", "-o", temp_file.name,
            "--cookies", "/mnt/data/cookies.txt", video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("yt-dlp error: %s", result.stderr)
            return None, temp_file.name
        logging.info(f"✅ Audio converted to {temp_file.name}")
        return temp_file.name, temp_file.name
    except Exception:
        logging.exception("Error converting video to MP3")
        return None, None

# Flask route to stream audio from a specific channel
@app.route("/<channel>.mp3")
def stream_mp3(channel):
    logging.info(f"Streaming started for {channel}")

    channel_url = CHANNELS.get(channel)
    if not channel_url:
        return f"Channel '{channel}' not found", 404

    # Step 1: Fetch the latest video URL
    video_url = fetch_latest_video_url(channel_url)
    if not video_url:
        return "Could not fetch latest video URL", 503

    # Step 2: Convert the video to MP3 and save it temporarily
    mp3_file, temp_file_path = convert_to_mp3(video_url)
    if not mp3_file:
        return "Error converting video to MP3", 500

    # Step 3: Stream the MP3 from the temporary file
    def generate_stream(file_path):
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                yield chunk
                time.sleep(0.02)  # prevent buffer overrun

    # Step 4: After streaming is done, delete the temporary file
    def delete_temp_file():
        os.remove(temp_file_path)
        logging.info(f"Temporary file {temp_file_path} deleted")

    # Start streaming and schedule deletion after playback
    response = Response(generate_stream(mp3_file), mimetype="audio/mpeg")
    response.call_on_close(delete_temp_file)

    return response

# Home route to list available streams
@app.route("/")
def index():
    links = [f'<li><a href="/{ch}.mp3">{ch}.mp3</a></li>' for ch in CHANNELS]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

# Start the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)