import os import time import json import subprocess import logging import threading from flask import Flask, Response, request, redirect from pathlib import Path from urllib.parse import quote_plus

app = Flask(name) logging.basicConfig(level=logging.INFO)

REFRESH_INTERVAL = 1200 RECHECK_INTERVAL = 3600 EXPIRE_AGE = 7200 FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

TMP_DIR = Path("/tmp/ytmp3") TMP_DIR.mkdir(exist_ok=True)

VIDEO_CACHE = {} LAST_VIDEO_ID = {}

@app.route("/search") def search(): query = request.args.get("q", "").strip() if not query: return "<h3>Enter a search query</h3>", 400

cmd = [
    "yt-dlp",
    "ytsearch5:" + query,
    "--dump-json",
    "--cookies", "/mnt/data/cookies.txt",
    "--user-agent", FIXED_USER_AGENT
]
try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    entries = [json.loads(line) for line in result.stdout.strip().splitlines() if line.strip()]
except Exception as e:
    logging.error(f"Search error: {e}")
    return f"<h3>Error performing search</h3>{e}", 500

html = f"""
<html><head><title>Search results for '{query}'</title></head>
<body style='font-family:sans-serif;'>
<h3>Search results for '{query}'</h3>
<form method='get' action='/search'>
    <input type='text' name='q' value='{query}' placeholder='Search YouTube'>
    <input type='submit' value='Search'>
</form><br>
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

@app.route("/download") def download(): video_id = request.args.get("q") if not video_id: return "Missing video ID", 400

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

def generate():
    with open(mp3_path, "rb") as f:
        yield from f

return Response(generate(), mimetype="audio/mpeg")

@app.route("/") def index(): return """ <html><head><title>YouTube MP3</title></head> <body style='font-family:sans-serif;'> <h3>YouTube MP3 Search</h3> <form method='get' action='/search'> <input type='text' name='q' placeholder='Search YouTube...'> <input type='submit' value='Search'> </form> </body></html> """

if name == "main": app.run(host="0.0.0.0", port=8000)

