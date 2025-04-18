from flask import Flask, Response
import subprocess
import json
import os
import logging
import time
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

CHANNELS = {
    "babu": "https://www.youtube.com/@babu_ramachandran/videos",
    "ddm": "https://www.youtube.com/@DoordarshanMalayalam/videos",
    "furqan": "https://www.youtube.com/@alfurqan4991/videos"
}

CACHE = {
    name: {"url": None, "stream_url": None, "last_checked": 0}
    for name in CHANNELS
}

def fetch_latest_video_url(channel_url):
    try:
        cmd = [
            "yt-dlp", "--flat-playlist", "--playlist-end", "1",
            "--dump-single-json", "--cookies", "/mnt/data/cookies.txt",
            channel_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("yt-dlp error for %s: %s", channel_url, result.stderr)
            return None
        data = json.loads(result.stdout)
        video_id = data["entries"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        logging.exception("Error fetching latest video URL")
        return None

def get_youtube_audio_url(youtube_url):
    try:
        command = [
            "/usr/local/bin/yt-dlp", "--cookies", "/mnt/data/cookies.txt",
            "-f", "bestaudio", "-g", youtube_url
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logging.error("yt-dlp audio extract error: %s", result.stderr)
            return None
    except Exception:
        logging.exception("Error extracting audio URL")
        return None

def update_cache(name, channel_url):
    while True:
        logging.info(f"Refreshing for {name}...")
        video_url = fetch_latest_video_url(channel_url)
        if video_url:
            stream_url = get_youtube_audio_url(video_url)
            if stream_url:
                CACHE[name] = {
                    "url": video_url,
                    "stream_url": stream_url,
                    "last_checked": time.time()
                }
                logging.info(f"✅ [{name}] {video_url} -> {stream_url}")
            else:
                logging.warning(f"❌ [{name}] Could not get stream URL")
        else:
            logging.warning(f"❌ [{name}] Could not fetch video URL")
        time.sleep(1800)

# Launch one thread per channel
for name, url in CHANNELS.items():
    threading.Thread(target=update_cache, args=(name, url), daemon=True).start()

def generate_stream(url):
    while True:
        process = subprocess.Popen([
            "ffmpeg", "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10",
            "-user_agent", "Mozilla/5.0", "-i", url, "-vn", "-ac", "1",
            "-b:a", "64k", "-bufsize", "1M", "-f", "mp3", "-"
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

@app.route("/<name>.mp3")
def stream_by_name(name):
    if name not in CACHE:
        return f"No stream configured for '{name}'", 404
    stream_url = CACHE[name]["stream_url"]
    if not stream_url:
        return f"Stream '{name}' not ready", 503
    return Response(generate_stream(stream_url), mimetype="audio/mpeg")

@app.route("/")
def index():
    html = "<h3>Live YouTube Channel Audio Streams</h3><ul>"
    for name in CHANNELS:
        html += f'<li><a href="/{name}.mp3">{name}.mp3</a></li>'
    html += "</ul>"
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)