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
    "vallathorukatha": "https://www.youtube.com/@babu_ramachandran/videos",
    "ddm": "https://www.youtube.com/@ddmalayalamtv/videos",
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

VIDEO_CACHE = {name: {"url": None, "stream_url": None, "last_checked": 0} for name in CHANNELS}

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

def get_best_audio_url(video_url):
    try:
        cmd = [
            "yt-dlp", "-f", "bestaudio", "-g", "--cookies", "/mnt/data/cookies.txt", video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logging.error("yt-dlp error (fallback URL): %s", result.stderr)
            return None
    except Exception:
        logging.exception("Error extracting best audio URL")
        return None

def get_audio_process(video_url):
    try:
        cmd = [
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "-o", "-",
            "--cookies", "/mnt/data/cookies.txt",
            video_url
        ]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:
        logging.exception("Error starting yt-dlp audio process")
        return None

def generate_stream(video_url, fallback_url=None):
    process = get_audio_process(video_url)

    if process:
        logging.info("▶ Streaming full MP3 via yt-dlp")
        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                yield chunk
                time.sleep(0.02)
        except GeneratorExit:
            pass
        except Exception:
            logging.exception("yt-dlp stream failed, falling back...")
        finally:
            process.terminate()
            process.wait()

    # Fallback if yt-dlp -o - fails
    if fallback_url:
        logging.info("▶ Using fallback URL stream...")
        ffmpeg_cmd = [
            "ffmpeg", "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "30",
            "-user_agent", "Mozilla/5.0",
            "-i", fallback_url,
            "-vn", "-ac", "1", "-b:a", "40k", "-bufsize", "5M",
            "-probesize", "5000000", "-analyzeduration", "10000000",
            "-f", "mp3", "-"
        ]
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                yield chunk
                time.sleep(0.02)
        except GeneratorExit:
            pass
        except Exception:
            logging.exception("Fallback stream also failed.")
        finally:
            process.terminate()
            process.wait()

def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            logging.info(f"Refreshing for {name}...")
            video_url = fetch_latest_video_url(url)
            if video_url:
                stream_url = get_best_audio_url(video_url)
                VIDEO_CACHE[name].update({
                    "url": video_url,
                    "stream_url": stream_url,
                    "last_checked": time.time()
                })
                logging.info(f"✅ {name}: {video_url}")
            else:
                logging.warning(f"❌ Could not fetch video URL for {name}")
        time.sleep(1800)  # Refresh every 30 min

threading.Thread(target=update_video_cache_loop, daemon=True).start()

@app.route("/<channel>.mp3")
def stream_mp3(channel):
    data = VIDEO_CACHE.get(channel)
    if not data or not data.get("url"):
        return f"Stream for '{channel}' not ready", 503
    return Response(generate_stream(data["url"], data.get("stream_url")), mimetype="audio/mpeg")

@app.route("/")
def index():
    links = [f'<li><a href="/{ch}.mp3">{ch}.mp3</a></li>' for ch in CHANNELS]
    return f"<h3>Available Streams</h3><ul>{''.join(links)}</ul>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)