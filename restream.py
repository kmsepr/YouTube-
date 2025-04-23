import os
import json
import subprocess
import logging
import time
import html
from flask import Flask, request, Response, redirect
from pathlib import Path
from urllib.parse import quote_plus
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Directories and settings
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)
FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
EXPIRE_AGE = 7200  # 2 hours

if not YOUTUBE_API_KEY:
    raise ValueError("YouTube API key is missing. Please set the YOUTUBE_API_KEY environment variable.")

# Utility Functions
def get_cached_files():
    """Fetch cached MP3/MP4 files sorted by modified time (most recent first)."""
    return sorted(TMP_DIR.glob("*.mp3"), key=lambda x: x.stat().st_mtime, reverse=True)

def cleanup_old_files():
    """Cleanup files older than EXPIRE_AGE seconds."""
    now = time.time()
    for file in TMP_DIR.glob("*"):
        if file.stat().st_mtime < now - EXPIRE_AGE:
            logging.info(f"Deleting old file: {file}")
            file.unlink()

# Routes
@app.route("/")
def index():
    search_html = """
    <form method='get' action='/search'>
        <input type='text' name='q' placeholder='Search YouTube...'>
        <input type='submit' value='Search'>
    </form><br>
    """

    cached_html = "<h3>Cached MP3s</h3>"
    for file in get_cached_files():
        video_id = file.stem
        cached_html += f"""
        <div style='margin-bottom:10px;'>
            <img src='https://i.ytimg.com/vi/{video_id}/mqdefault.jpg' width='120'><br>
            <a href='/download?q={video_id}'>{html.escape(video_id)}</a>
        </div>
        """

    return f"<html><body style='font-family:sans-serif;'>{search_html}{cached_html}</body></html>"

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect("/")

    # YouTube API search query
    url = f"https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": 5
    }

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        results = r.json().get("items", [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching search results: {e}")
        return f"<h3>Error fetching search results: {e}</h3>", 500

    html_response = f"""
    <html><head><title>Search results for '{query}'</title></head>
    <body style='font-family:sans-serif;'>
    <form method='get' action='/search'>
        <input type='text' name='q' value='{html.escape(query)}' placeholder='Search YouTube'>
        <input type='submit' value='Search'>
    </form><br>
    <h3>Search results for '{html.escape(query)}'</h3>
    """

    for item in results:
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumbnail = item["snippet"]["thumbnails"]["medium"]["url"]
        html_response += f"""
        <div style='margin-bottom:10px;'>
            <img src='{thumbnail}' width='120'><br>
            {html.escape(title)}<br>
            <a href='/download?q={quote_plus(video_id)}'>Download MP3</a> |
            <a href='/download_mp4?q={quote_plus(video_id)}'>Download MP4</a>
        </div>
        """
    html_response += "</body></html>"
    return html_response

@app.route("/download")
def download():
    video_id = request.args.get("q")
    if not video_id:
        return "Missing video ID", 400

    mp3_path = TMP_DIR / f"{video_id}.mp3"
    if not mp3_path.exists():
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            subprocess.run([
                "yt-dlp", "-f", "bestaudio",
                "--output", str(TMP_DIR / f"{video_id}.%(ext)s"),
                "--user-agent", FIXED_USER_AGENT,
                "--postprocessor-args", "-ar 22050 -ac 1 -b:a 40k",
                "--extract-audio",
                "--audio-format", "mp3",
                url
            ], check=True)
        except Exception as e:
            logging.error(f"Download error: {e}")
            return f"Download error: {e}", 500

    if not mp3_path.exists():
        return "File not available", 500

    def generate():
        with open(mp3_path, "rb") as f:
            yield from f

    return Response(generate(), mimetype="audio/mpeg")

@app.route("/download_mp4")
def download_mp4():
    video_id = request.args.get("q")
    if not video_id:
        return "Missing video ID", 400

    mp4_path = TMP_DIR / f"{video_id}_320x240.mp4"
    if not mp4_path.exists():
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            subprocess.run([
                "yt-dlp", "-f", "bestvideo[height<=240]+bestaudio/best",
                "--output", str(TMP_DIR / f"{video_id}_320x240.%(ext)s"),
                "--user-agent", FIXED_USER_AGENT,
                "--postprocessor-args", "-vf scale=320:240",
                url
            ], check=True)
        except Exception as e:
            logging.error(f"Download error: {e}")
            return f"Download error: {e}", 500

    if not mp4_path.exists():
        return "File not available", 500

    def generate():
        with open(mp4_path, "rb") as f:
            yield from f

    return Response(generate(), mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)