from flask import Flask, Response
import subprocess
import json
import logging
import time
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# YouTube channel list
CHANNELS = {
    "qasimi": "https://www.youtube.com/@quranstudycentremukkam/videos",
    "sharique": "https://www.youtube.com/@shariquesamsudheen/videos",
    "drali": "https://www.youtube.com/@draligomaa/videos",
    "yaqeen": "https://youtube.com/@yaqeeninstituteofficial/videos",
    "talent": "https://youtube.com/@talentacademyonline/videos",
    "suprabhatam": "https://youtube.com/@suprabhaatham2023/videos",
    "bayyinah": "https://youtube.com/@bayyinah/videos",
    "zamzam": "https://youtube.com/@zamzamacademy/videos",
    "jrstudio": "https://youtube.com/@jrstudiomalayalam/videos",

"raftalks": "https://youtube.com/@raftalksmalayalam/videos",
    "parvinder": "https://www.youtube.com/@pravindersheoran/videos",
    "vallathorukatha": "https://www.youtube.com/@babu_ramachandran/videos",
    "furqan": "https://youtube.com/@alfurqan4991/videos",
    "skicr": "https://youtube.com/@skicrtv/videos",
    "dhruvrathee": "https://youtube.com/@dhruvrathee/videos",
    "safari": "https://youtube.com/@safaritvlive/videos",
    "sunnxt": "https://youtube.com/@sunnxtmalayalam/videos",
    "movieworld": "https://youtube.com/@movieworldmalayalammovies/videos",
    "comedy": "https://youtube.com/@malayalamcomedyscene5334/videos",
    "studyiq": "https://youtube.com/@studyiqiasenglish/videos",
    "vijayakumarblathur": "https://youtube.com/@vijayakumarblathur/videos",

"entridegree": "https://youtube.com/@entridegreelevelexams/videos",
}

# Cache to store latest video info per channel
VIDEO_CACHE = {name: {"url": None, "stream_url": None, "last_checked": 0} for name in CHANNELS}

# Get latest video URL
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

# Get direct audio stream URL
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

# Background thread to refresh cache every 30 minutes
def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            logging.info(f"Refreshing {name}...")
            video_url = fetch_latest_video_url(url)
            if video_url:
                stream_url = get_best_audio_url(video_url)
                if stream_url:
                    VIDEO_CACHE[name] = {
                        "url": video_url,
                        "stream_url": stream_url,
                        "last_checked": time.time()
                    }
                    logging.info(f"✅ {name}: {video_url} -> {stream_url}")
                else:
                    logging.warning(f"❌ Failed stream URL for {name}")
            else:
                logging.warning(f"❌ Failed video fetch for {name}")
        time.sleep(1800)  # 30 minutes

threading.Thread(target=update_video_cache_loop, daemon=True).start()

# FFMPEG stream generator
def generate_stream(url):
    process = subprocess.Popen([
        "ffmpeg",
        "-user_agent", "Mozilla/5.0",
        "-i", url,
        "-vn", "-ac", "1", "-b:a", "40k", "-bufsize", "1M", "-f", "mp3", "-"
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    try:
        while True:
            if process.poll() is not None:
                break  # FFmpeg process ended
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            yield chunk
            time.sleep(0.02)
    except GeneratorExit:
        process.terminate()
    except Exception:
        process.terminate()
    finally:
        process.wait()

# Stream route
@app.route("/<channel>.mp3")
def stream_mp3(channel):
    if channel not in CHANNELS:
        return "Invalid channel", 404

    data = VIDEO_CACHE[channel]

    # Refresh if cache is over 1 hour old
    if time.time() - data["last_checked"] > 3600:
        video_url = fetch_latest_video_url(CHANNELS[channel])
        stream_url = get_best_audio_url(video_url) if video_url else None
        if video_url and stream_url:
            VIDEO_CACHE[channel] = {
                "url": video_url,
                "stream_url": stream_url,
                "last_checked": time.time()
            }
        else:
            return f"Could not refresh stream for '{channel}'", 503

    return Response(generate_stream(VIDEO_CACHE[channel]["stream_url"]), mimetype="audio/mpeg")

# Home route
@app.route("/")
def index():
    links = [f'<li><a href="/{ch}.mp3">{ch}.mp3</a></li>' for ch in CHANNELS]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

# Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)