import html
import time
import requests
import subprocess
from flask import Flask, request, Response, redirect
from pathlib import Path
from urllib.parse import quote_plus
import os

app = Flask(__name__)
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
CACHE_TTL = 3600  # Cache cleanup in 1 hour

def clean_old_files():
    now = time.time()
    for f in TMP_DIR.glob("*.*"):
        if f.is_file() and now - f.stat().st_mtime > CACHE_TTL:
            try:
                f.unlink()
            except Exception:
                pass

def get_cached_files():
    return sorted(TMP_DIR.glob("*.mp3"), key=lambda f: f.stat().st_mtime, reverse=True)

@app.route("/")
def index():
    clean_old_files()
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
            <a href='/download?q={video_id}'>{video_id}</a>
        </div>
        """

    return f"<html><body style='font-family:sans-serif;'>{search_html}{cached_html}</body></html>"

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect("/")

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
        r.raise_for_status()  # Raise exception for HTTP error responses
        results = r.json().get("items", [])
    except requests.exceptions.RequestException as e:
        return f"<h3>Error accessing YouTube API: {e}</h3>", 500
    except Exception as e:
        return f"<h3>Unexpected error: {e}</h3>", 500

    html = f"""
    <html><head><title>Search results for '{html.escape(query)}'</title></head>
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
        html += f"""
        <div style='margin-bottom:10px;'>
            <img src='{thumbnail}' width='120'><br>
            {html.escape(title)}<br>
            <a href='/download?q={quote_plus(video_id)}'>Download MP3</a> |
            <a href='/download_mp4?q={quote_plus(video_id)}'>Download MP4</a>
        </div>
        """
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

    mp4_path = TMP_DIR / f"{video_id}.mp4"
    if not mp4_path.exists():
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            subprocess.run([
                "yt-dlp", "-f", "18",  # format 18 = 360p MP4
                "--output", str(mp4_path),
                "--user-agent", FIXED_USER_AGENT,
            ], check=True)
        except Exception as e:
            return f"Download error: {e}", 500

    if not mp4_path.exists():
        return "File not available", 500

    def generate():
        with open(mp4_path, "rb") as f:
            yield from f

    return Response(generate(), mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)