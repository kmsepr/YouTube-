import os
import time
import json
import logging
import subprocess
from flask import Flask, request, Response, redirect
from pathlib import Path
from urllib.parse import quote_plus
import requests

app = Flask(__name__)
TMP_DIR = Path("/mnt/data/ytmp3")  # Persistent storage
TMP_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL = 6 * 3600  # 6 hours
TITLE_CACHE_FILE = TMP_DIR / "titles.json"
FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
logging.basicConfig(level=logging.DEBUG)

# Load title cache
if TITLE_CACHE_FILE.exists():
    with open(TITLE_CACHE_FILE, "r") as f:
        TITLE_CACHE = json.load(f)
else:
    TITLE_CACHE = {}

def save_title_cache():
    with open(TITLE_CACHE_FILE, "w") as f:
        json.dump(TITLE_CACHE, f)

def clean_old_files():
    now = time.time()
    for f in TMP_DIR.glob("*.mp3"):
        if now - f.stat().st_mtime > CACHE_TTL:
            try:
                f.unlink()
                TITLE_CACHE.pop(f.stem, None)
            except Exception as e:
                logging.error(f"Failed to delete {f}: {e}")
    save_title_cache()

def get_cached_files():
    return [f for f in TMP_DIR.glob("*.mp3")]

@app.route("/")
def index():
    clean_old_files()
    search_html = """<form method='get' action='/search'>
    <input type='text' name='q' placeholder='Search YouTube...'>
    <input type='submit' value='Search'></form><br>"""

    cached_html = "<h3>Cached MP3s</h3>"
    for file in get_cached_files():
        video_id = file.stem
        title = TITLE_CACHE.get(video_id, video_id)
        cached_html += f"""
        <div style='margin-bottom:10px;'>
            <img src='https://i.ytimg.com/vi/{video_id}/mqdefault.jpg' width='120'><br>
            {title}<br>
            <a href='/download?q={video_id}'>Download MP3</a>
        </div>
        """
    return f"<html><body style='font-family:sans-serif;'>{search_html}{cached_html}</body></html>"

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect("/")

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": 5
    }

    r = requests.get(url, params=params)
    results = r.json().get("items", [])

    html = f"""
    <html><head><title>Search results for '{query}'</title></head>
    <body style='font-family:sans-serif;'>
    <form method='get' action='/search'>
        <input type='text' name='q' value='{query}' placeholder='Search YouTube'>
        <input type='submit' value='Search'>
    </form><br><h3>Search results for '{query}'</h3>
    """

    for item in results:
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
        TITLE_CACHE[video_id] = title
        html += f"""
        <div style='margin-bottom:10px;'>
            <img src='{thumbnail}' width='120'><br>
            {title}<br>
            <a href='/download?q={quote_plus(video_id)}'>Download MP3</a>
        </div>
        """
    save_title_cache()
    html += "</body></html>"
    return html

@app.route("/download")
def download():
    video_id = request.args.get("q")
    if not video_id:
        return "Missing video ID", 400

    mp3_path = TMP_DIR / f"{video_id}.mp3"
    if not mp3_path.exists():
        url = f"https://www.youtube.com/watch?v={video_id}"
        cookies_path = "/mnt/data/cookies.txt"

        if not Path(cookies_path).exists():
            logging.error("Cookies file not found")
            return "Cookies file not found", 400

        try:
            subprocess.run([
                "yt-dlp", "-f", "bestaudio",
                "--output", str(TMP_DIR / f"{video_id}.%(ext)s"),
                "--user-agent", FIXED_USER_AGENT,
                "--postprocessor-args", "-ar 22050 -ac 1 -b:a 40k",
                "--extract-audio", "--audio-format", "mp3",
                "--cookies", cookies_path,
                url
            ], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Download failed: {e}")
            return "Download failed", 500

    if not mp3_path.exists():
        return "File not available", 500

    def generate():
        with open(mp3_path, "rb") as f:
            yield from f

    return Response(generate(), mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)