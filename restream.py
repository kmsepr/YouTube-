import os
import json
import logging
import subprocess
from flask import Flask, request, Response, redirect
from pathlib import Path
from urllib.parse import quote_plus, unquote
import requests

app = Flask(__name__)
TMP_DIR = Path("/tmp/ytmp3")
META_PATH = TMP_DIR / "meta.json"
TMP_DIR.mkdir(exist_ok=True)
if not META_PATH.exists():
    META_PATH.write_text("{}", encoding="utf-8")

FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

logging.basicConfig(level=logging.DEBUG)

def load_meta():
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except:
        return {}

def save_meta(meta):
    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

def get_cached_files():
    meta = load_meta()
    cached = []
    for file in TMP_DIR.glob("*.mp3"):
        for vid, title in meta.items():
            if file.name.endswith(f"{vid}].mp3"):
                cached.append((vid, title, file.name))
    return cached

@app.route("/")
def index():
    search_html = """<form method='get' action='/search'>
    <input type='text' name='q' placeholder='Search YouTube...'>
    <input type='submit' value='Search'></form><br>"""

    cached_html = "<h3>Cached MP3s</h3>"
    for video_id, title, filename in get_cached_files():
        cached_html += f"""
        <div style='margin-bottom:10px;'>
            <img src='https://i.ytimg.com/vi/{video_id}/mqdefault.jpg' width='120'><br>
            <b>{title}</b><br>
            <a href='/download?q={video_id}'>{filename}</a>
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
        html += f"""
        <div style='margin-bottom:10px;'>
            <img src='{thumbnail}' width='120'><br>
            {title}<br>
            <a href='/download?q={quote_plus(video_id)}'>Download MP3</a>
        </div>
        """
    html += "</body></html>"
    return html

@app.route("/download")
def download():
    video_id = request.args.get("q")
    if not video_id:
        return "Missing video ID", 400

    meta = load_meta()
    if video_id in meta:
        title = meta[video_id]
    else:
        # Get metadata only
        try:
            logging.info(f"Fetching metadata for {video_id}")
            result = subprocess.run([
                "yt-dlp", f"https://www.youtube.com/watch?v={video_id}",
                "--skip-download", "--print", "%(title)s"
            ], check=True, capture_output=True, text=True)
            title = result.stdout.strip()
            meta[video_id] = title
            save_meta(meta)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get title: {e}")
            return "Metadata fetch failed", 500

    filename = f"{title} [{video_id}].mp3"
    mp3_path = TMP_DIR / filename

    if not mp3_path.exists():
        url = f"https://www.youtube.com/watch?v={video_id}"
        cookies_path = "/mnt/data/cookies.txt"
        logging.debug(f"Using cookies from: {cookies_path}")

        if not Path(cookies_path).exists():
            logging.error(f"Cookies file does not exist at {cookies_path}")
            return "Cookies file not found.", 400

        try:
            subprocess.run([
                "yt-dlp", "-f", "bestaudio",
                "--output", str(TMP_DIR / f"{title} [{video_id}].%(ext)s"),
                "--user-agent", FIXED_USER_AGENT,
                "--postprocessor-args", "-ar 22050 -ac 1 -b:a 40k",
                "--extract-audio",
                "--audio-format", "mp3",
                "--cookies", cookies_path,
                url
            ], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Download failed: {e}")
            return "Failed to download", 500

    if not mp3_path.exists():
        return "File not available", 500

    def generate():
        with open(mp3_path, "rb") as f:
            yield from f

    return Response(generate(), mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)