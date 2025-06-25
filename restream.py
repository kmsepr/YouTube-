from flask import Flask, Response, request
import os
import time
import json
import subprocess
import logging
import threading
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

REFRESH_INTERVAL = 1200
RECHECK_INTERVAL = 3600
EXPIRE_AGE = 7200
FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

CHANNELS = {
    "drali": "https://youtube.com/@draligomaa/videos",
    "suprabhatam": "https://youtube.com/@suprabhaatham2023/videos"
}

VIDEO_CACHE = {
    name: {
        "url": None, "last_checked": 0, "thumbnail": "",
        "upload_date": "", "title": "", "channel": ""
    } for name in CHANNELS
}
LAST_VIDEO_ID = {name: None for name in CHANNELS}
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

@app.route("/")
def index():
    html = """
    <html>
    <head>
        <title>YouTube Mp3</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; padding-top: 80px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; padding: 10px; }
            .card { border: 1px solid #ccc; border-radius: 8px; padding: 6px; background: #f9f9f9; }
            .card img { width: 100%; height: auto; border-radius: 4px; }
            .card a { text-decoration: none; font-weight: bold; }
            .fixed-player {
                position: fixed; top: 0; left: 0; right: 0;
                background: #222; color: #fff;
                padding: 10px; z-index: 1000;
                display: flex; flex-direction: column; align-items: center;
            }
            .fixed-player audio { width: 100%; max-width: 320px; }
        </style>
    </head>
    <body>
        <div class="fixed-player" id="playerBar" style="display:none;">
            <small>Last played:</small>
            <audio controls id="mainPlayer"></audio>
        </div>
        <h3 style='text-align:center;'>YouTube Mp3</h3>
        <div class="grid">
    """

    def get_upload_date(ch): return VIDEO_CACHE[ch].get("upload_date", "Unknown")

    for ch in sorted(CHANNELS, key=get_upload_date, reverse=True):
        mp3_path = TMP_DIR / f"{ch}.mp3"
        if not mp3_path.exists():
            continue
        thumb = VIDEO_CACHE[ch].get("thumbnail", "http://via.placeholder.com/120x80?text=YT").replace("https://", "http://")
        html += f"""
        <div class='card'>
            <img src='{thumb}' loading='lazy'>
            <div style='text-align:center;'>
                <a href='/play/{ch}'>{ch}</a>
            </div>
        </div>
        """

    html += """
        </div>
        <script>
            document.addEventListener("DOMContentLoaded", () => {
                const mainPlayer = document.getElementById("mainPlayer");
                const playerBar = document.getElementById("playerBar");
                const last = localStorage.getItem("last_played_audio");
                if (last) {
                    mainPlayer.src = last;
                    const pos = localStorage.getItem("pos_" + last);
                    if (pos) mainPlayer.currentTime = parseFloat(pos);
                    mainPlayer.ontimeupdate = () => {
                        localStorage.setItem("pos_" + last, mainPlayer.currentTime);
                    };
                    playerBar.style.display = "flex";
                }
                document.addEventListener("keydown", (e) => {
                    if (e.key === "1") {
                        playerBar.style.display = (playerBar.style.display === "none") ? "flex" : "none";
                    }
                });
            });
        </script>
    </body></html>
    """
    return html

@app.route("/play/<channel>")
def play_screen(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404
    data = VIDEO_CACHE.get(channel, {})
    title = data.get("title", channel)
    thumbnail = (data.get("thumbnail") or "http://via.placeholder.com/320x180?text=YT").replace("https://", "http://")
    mp3_url = f"/{channel}.mp3"
    return f"""
    <html><head><title>{title}</title>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>
        body {{ font-family: sans-serif; padding: 20px; text-align: center; }}
        img {{ max-width: 320px; border-radius: 10px; }}
        audio {{ width: 100%; margin-top: 20px; }}
        .back {{ display: inline-block; margin-bottom: 10px; padding: 8px 12px; background: #222; color: #fff; text-decoration: none; border-radius: 6px; }}
    </style></head><body>
    <a class='back' href='/'>← Back</a>
    <h2>{title}</h2>
    <img src='{thumbnail}'><br>
    <audio controls id='player'><source src='{mp3_url}' type='audio/mpeg'></audio>
    <script>
        const player = document.getElementById("player");
        const key = "pos_" + player.src;
        const saved = localStorage.getItem(key);
        if (saved) player.currentTime = parseFloat(saved);
        player.ontimeupdate = () => {{
            localStorage.setItem(key, player.currentTime);
            localStorage.setItem("last_played_audio", player.src);
        }};
    </script>
    </body></html>
    """

@app.route("/<channel>.mp3")
def stream_mp3(channel):
    path = TMP_DIR / f"{channel}.mp3"
    if not path.exists():
        return "Not found", 404
    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)
    headers = {'Content-Type': 'audio/mpeg', 'Accept-Ranges': 'bytes'}
    if range_header:
        byte1, byte2 = range_header.replace("bytes=", "").split("-")
        byte1 = int(byte1)
        byte2 = int(byte2) if byte2 else file_size - 1
        length = byte2 - byte1 + 1
        with open(path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)
        headers.update({
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Content-Length': str(length)
        })
        return Response(data, status=206, headers=headers)
    else:
        with open(path, 'rb') as f:
            data = f.read()
        headers['Content-Length'] = str(file_size)
        return Response(data, headers=headers)

# Add your yt-dlp, update cache, and background thread logic below here

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)