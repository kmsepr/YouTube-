import os
import time
import subprocess
import logging
import threading
from flask import Flask, Response, request
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Interval settings
REFRESH_INTERVAL = 1200   # 20 minutes
RECHECK_INTERVAL  = 3600  # 60 minutes
EXPIRE_AGE        = 7200  # 2 hours

# Fixed user agent
FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# Your channels
CHANNELS = {
    "maheen":       "https://youtube.com/@hitchhikingnomaad/videos",
    "entri":        "https://youtube.com/@entriapp/videos",
    # …etc…
    "studyiq":      "https://youtube.com/@studyiqiasenglish/videos",
}

# In-memory cache for URL, thumbnail URL & upload date
VIDEO_CACHE    = {c: {"url": None, "thumbnail": "", "upload_date": ""} for c in CHANNELS}
LAST_VIDEO_ID  = {c: None for c in CHANNELS}

# Where MP3s get stored
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

def fetch_latest_video_url(name, channel_url):
    """Use yt-dlp to get the latest video URL, thumbnail & upload_date."""
    try:
        out = subprocess.run([
            "yt-dlp",
            "--dump-single-json",
            "--playlist-end", "1",
            "--cookies", "/mnt/data/cookies.txt",
            "--user-agent", FIXED_USER_AGENT,
            channel_url
        ], capture_output=True, text=True, check=True).stdout
        data   = __import__("json").loads(out)
        entry  = data["entries"][0]
        vid    = entry["id"]
        thumb  = entry.get("thumbnail", "")
        updt   = entry.get("upload_date", "")
        return f"https://www.youtube.com/watch?v={vid}", thumb, vid, updt
    except Exception as e:
        logging.error(f"fetch_latest({name}) error: {e}")
        return None, None, None, None

def download_and_convert(channel, video_url):
    """
    Uses yt-dlp to:
      1) download best audio
      2) convert to mp3
      3) embed thumbnail + metadata
    """
    final_mp3 = TMP_DIR / f"{channel}.mp3"
    if final_mp3.exists():
        return final_mp3
    if not video_url:
        return None

    try:
        subprocess.run([
            "yt-dlp",
            "-f", "bestaudio",
            "-o", str(final_mp3.with_suffix(".%(ext)s")),
            "--cookies", "/mnt/data/cookies.txt",
            "--user-agent", FIXED_USER_AGENT,
            "-x",                    # extract audio
            "--audio-format", "mp3",
            "--embed-thumbnail",     # download & embed YT thumbnail
            "--embed-metadata",      # embed title/artist metadata
            "--prefer-ffmpeg",       # use ffmpeg backend
            video_url
        ], check=True)

        return final_mp3 if final_mp3.exists() else None

    except Exception as e:
        logging.error(f"download_and_convert({channel}) error: {e}")
        # cleanup any partial files
        for ext in [".mp3.part", ".webm", ".m4a", ".ogg"]:
            p = TMP_DIR / f"{channel}{ext}"
            if p.exists():
                p.unlink()
        return None

def cleanup_old_files():
    while True:
        now = time.time()
        for f in TMP_DIR.glob("*.mp3"):
            if now - f.stat().st_mtime > EXPIRE_AGE:
                try:
                    logging.info(f"Removing old file {f.name}")
                    f.unlink()
                except:
                    pass
        time.sleep(EXPIRE_AGE)

def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            video_url, thumb, vid, updt = fetch_latest_video_url(name, url)
            if video_url and vid and LAST_VIDEO_ID[name] != vid:
                LAST_VIDEO_ID[name] = vid
                VIDEO_CACHE[name].update(url=video_url, thumbnail=thumb, upload_date=updt)
                download_and_convert(name, video_url)
            time.sleep(2)
        time.sleep(REFRESH_INTERVAL)

def auto_download_mp3s():
    while True:
        for name, data in VIDEO_CACHE.items():
            mp3_path = TMP_DIR / f"{name}.mp3"
            if data["url"] and (not mp3_path.exists() or
               time.time() - mp3_path.stat().st_mtime > RECHECK_INTERVAL):
                logging.info(f"Auto-updating {name}.mp3")
                download_and_convert(name, data["url"])
            time.sleep(2)
        time.sleep(RECHECK_INTERVAL)

@app.route("/<channel>.mp3")
def stream_mp3(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    mp3_path = TMP_DIR / f"{channel}.mp3"
    if not mp3_path.exists():
        # fetch & convert on-the-fly
        url, thumb, vid, updt = fetch_latest_video_url(channel, CHANNELS[channel])
        if not url:
            return "Failed to fetch video", 500
        VIDEO_CACHE[channel].update(url=url, thumbnail=thumb, upload_date=updt)
        LAST_VIDEO_ID[channel] = vid
        download_and_convert(channel, url)

    if not mp3_path.exists():
        return "Conversion error", 500

    file_size = os.path.getsize(mp3_path)
    range_hdr = request.headers.get("Range", None)
    headers   = {"Content-Type":"audio/mpeg","Accept-Ranges":"bytes"}

    if range_hdr:
        byte1, byte2 = range_hdr.replace("bytes=","").split("-")
        b1 = int(byte1)
        b2 = int(byte2) if byte2 else file_size-1
        length = b2 - b1 + 1
        with open(mp3_path,"rb") as f:
            f.seek(b1)
            chunk = f.read(length)
        headers.update({
            "Content-Range":f"bytes {b1}-{b2}/{file_size}",
            "Content-Length":str(length)
        })
        return Response(chunk, status=206, headers=headers)

    with open(mp3_path,"rb") as f:
        data = f.read()
    headers["Content-Length"] = str(file_size)
    return Response(data, headers=headers)

@app.route("/")
def index():
    html = """
    <html><head><title>YouTube MP3</title></head>
    <body style="font-family:sans-serif; font-size:14px;">
      <h2>YouTube MP3</h2>
      <div style="display:flex; flex-wrap:wrap;">
    """
    def ud(c): return VIDEO_CACHE[c].get("upload_date","Unknown")
    for c in sorted(CHANNELS, key=ud, reverse=True):
        mp = TMP_DIR / f"{c}.mp3"
        if not mp.exists(): continue
        thumb = VIDEO_CACHE[c].get("thumbnail") or "https://via.placeholder.com/120x80"
        html += f"""
        <div style="margin:8px; width:160px; text-align:center;">
          <img src="{thumb}" style="width:100%; border-radius:4px;" /><br>
          <a href="/{c}.mp3" style="text-decoration:none;">{c}</a><br>
          <small>{ud(c)}</small>
        </div>
        """
    html += "</div></body></html>"
    return html

if __name__ == "__main__":
    threading.Thread(target=cleanup_old_files, daemon=True).start()
    threading.Thread(target=update_video_cache_loop, daemon=True).start()
    threading.Thread(target=auto_download_mp3s, daemon=True).start()
    app.run(host="0.0.0.0", port=8000)