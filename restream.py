import os
import json
import subprocess
from pathlib import Path
from urllib.parse import quote_plus
from flask import Flask, request, Response

app = Flask(__name__)
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

TITLE_CACHE_PATH = TMP_DIR / "titles.json"
THUMBNAIL_CACHE_PATH = TMP_DIR / "thumbs.json"
VIDEO_CACHE = {}
THUMBNAIL_CACHE = {}

# Load caches
if TITLE_CACHE_PATH.exists():
    try:
        VIDEO_CACHE.update(json.loads(TITLE_CACHE_PATH.read_text()))
    except:
        pass

if THUMBNAIL_CACHE_PATH.exists():
    try:
        THUMBNAIL_CACHE.update(json.loads(THUMBNAIL_CACHE_PATH.read_text()))
    except:
        pass

FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def save_metadata(video_id, title, thumb):
    VIDEO_CACHE[video_id] = title
    THUMBNAIL_CACHE[video_id] = thumb
    TITLE_CACHE_PATH.write_text(json.dumps(VIDEO_CACHE))
    THUMBNAIL_CACHE_PATH.write_text(json.dumps(THUMBNAIL_CACHE))

@app.route("/")
def index():
    html = """
    <html><head><title>YouTube MP3</title></head>
    <body style='font-family:sans-serif;'>
    <h3>YouTube MP3 Search</h3>
    <form method='get' action='/search'>
        <input type='text' name='q' placeholder='Search YouTube...'>
        <input type='submit' value='Search'>
    </form><hr>
    <h4>Cached MP3s</h4>
    """
    for video_id, title in VIDEO_CACHE.items():
        thumb = THUMBNAIL_CACHE.get(video_id, "")
        html += f"""
        <div style='margin-bottom:10px;'>
            <img src='{thumb}' width='120'><br>
            <b>{title}</b><br>
            <a href='/download?q={video_id}'>Download/Stream MP3</a>
        </div>
        """
    html += "</body></html>"
    return html

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect("/")

    cmd = [
        "yt-dlp", "ytsearch5:" + query,
        "--dump-json",
        "--cookies", "/mnt/data/cookies.txt",
        "--user-agent", FIXED_USER_AGENT
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        entries = [json.loads(line) for line in result.stdout.strip().splitlines() if line.strip()]
    except Exception as e:
        return f"<h3>Search failed</h3><pre>{e}</pre><br><a href='/'>Go Home</a>", 500

    html = f"""
    <html><head><title>Search results for '{query}'</title></head>
    <body style='font-family:sans-serif;'>
    <form method='get' action='/search'>
        <input type='text' name='q' value='{query}' placeholder='Search YouTube'>
        <input type='submit' value='Search'>
    </form><hr>
    <h3>Search results for '{query}'</h3><br>
    """

    for entry in entries:
        video_id = entry.get("id")
        title = entry.get("title")
        thumbnail = entry.get("thumbnail")
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

    mp3_path = TMP_DIR / f"{video_id}.mp3"
    if not mp3_path.exists():
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            subprocess.run([
                "yt-dlp", "-f", "bestaudio",
                "--output", str(TMP_DIR / f"{video_id}.%(ext)s"),
                "--cookies", "/mnt/data/cookies.txt",
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

    # Add to cache
    if video_id not in VIDEO_CACHE:
        try:
            info = subprocess.run([
                "yt-dlp", "-j", "--cookies", "/mnt/data/cookies.txt",
                f"https://www.youtube.com/watch?v={video_id}"
            ], capture_output=True, text=True, check=True)
            data = json.loads(info.stdout)
            save_metadata(video_id, data.get("title", video_id), data.get("thumbnail", ""))
        except:
            save_metadata(video_id, video_id, "")

    def generate():
        with open(mp3_path, "rb") as f:
            yield from f

    return Response(generate(), mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)