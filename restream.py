import os
import time
import logging
import subprocess
from flask import Flask, request, Response, redirect
from pathlib import Path
from urllib.parse import quote_plus
import requests
import json

app = Flask(__name__)
TMP_DIR = Path("/mnt/data/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

TITLE_CACHE = TMP_DIR / "title_cache.json"
if not TITLE_CACHE.exists():
    TITLE_CACHE.write_text("{}", encoding="utf-8")

FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

logging.basicConfig(level=logging.DEBUG)

def save_title(video_id, title):
    try:
        cache = json.loads(TITLE_CACHE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    cache[video_id] = title
    TITLE_CACHE.write_text(json.dumps(cache), encoding="utf-8")

def load_title(video_id):
    try:
        cache = json.loads(TITLE_CACHE.read_text(encoding="utf-8"))
        return cache.get(video_id, video_id)
    except Exception:
        return video_id

def get_unique_video_ids():
    files = list(TMP_DIR.glob("*.mp3")) + list(TMP_DIR.glob("*.mp4"))
    unique_ids = {}
    for file in files:
        vid = file.stem.split("_")[0]
        if vid not in unique_ids:
            unique_ids[vid] = file
    return unique_ids

def safe_filename(name):
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in name)

@app.route("/")
def index():
    search_html = """<form method='get' action='/search'>
    <input type='text' name='q' placeholder='Search YouTube...'>
    <input type='submit' value='Search'></form><br>"""

    cached_html = "<h3>Cached Files</h3>"
    for video_id, file in get_unique_video_ids().items():
        ext = file.suffix.lstrip(".")
        title = load_title(video_id)
        cached_html += f"""
        <div style='margin-bottom:10px;'>
            <img src='https://i.ytimg.com/vi/{video_id}/mqdefault.jpg' width='120'><br>
            <b>{title}</b><br>
            <a href='/download?q={video_id}&fmt=mp3'>Download MP3</a> |
            <a href='/download?q={video_id}&fmt=mp4'>Download MP4</a>
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
        save_title(video_id, title)
        html += f"""
        <div style='margin-bottom:10px;'>
            <img src='{thumbnail}' width='120'><br>
            <b>{title}</b><br>
            <a href='/download?q={quote_plus(video_id)}&fmt=mp3'>Download MP3</a> |
            <a href='/download?q={quote_plus(video_id)}&fmt=mp4'>Download MP4</a>
        </div>
        """
    html += "</body></html>"
    return html

@app.route("/download")
def download():
    video_id = request.args.get("q")
    fmt = request.args.get("fmt", "mp3")
    if not video_id:
        return "Missing video ID", 400

    title = safe_filename(load_title(video_id))
    ext = "mp3" if fmt == "mp3" else "mp4"
    filename = f"{video_id}_{title}.{ext}"
    file_path = TMP_DIR / filename

    if not file_path.exists():
        url = f"https://www.youtube.com/watch?v={video_id}"
        cookies_path = "/mnt/data/cookies.txt"
        if not Path(cookies_path).exists():
            return "Cookies file not found", 400

        base_cmd = [
            "yt-dlp",
            "--output", str(TMP_DIR / f"{video_id}_{title}.%(ext)s"),
            "--user-agent", FIXED_USER_AGENT,
            "--cookies", cookies_path,
            url
        ]

        if fmt == "mp3":
            cmd = base_cmd[:1] + ["-f", "bestaudio"] + base_cmd[1:] + [
                "--postprocessor-args", "-ar 22050 -ac 1 -b:a 40k",
                "--extract-audio", "--audio-format", "mp3"
            ]
        else:
            cmd = base_cmd[:1] + ["-f", "best[ext=mp4]"] + base_cmd[1:] + [
                "--recode-video", "mp4",
                "--postprocessor-args", "-vf scale=320:240 -r 15 -b:v 384k -b:a 12k"
            ]

        success = False
        for attempt in range(3):
            try:
                logging.debug(f"Attempt {attempt + 1}: running yt-dlp...")
                subprocess.run(cmd, check=True)
                success = True
                break
            except subprocess.CalledProcessError as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(10)

        if not success or not file_path.exists():
            return "Download failed after retries", 500

    def generate():
        with open(file_path, "rb") as f:
            yield from f

    mimetype = "audio/mpeg" if fmt == "mp3" else "video/mp4"
    return Response(generate(), mimetype=mimetype, headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)