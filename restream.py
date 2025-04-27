import os
import time
import json
import subprocess
import logging
import threading
import requests
from flask import Flask, Response, request, send_file
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, error
from io import BytesIO

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Interval settings
REFRESH_INTERVAL = 1200       # 20 minutes
RECHECK_INTERVAL = 3600       # 60 minutes
EXPIRE_AGE = 7200             # 2 hours

# Fixed user agent
FIXED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

CHANNELS = {
"ccm": "https://youtube.com/@cambridgecentralmosque",

    "maheen": "https://youtube.com/@hitchhikingnomaad/videos",
    "entri": "https://youtube.com/@entriapp/videos",
    "zamzam": "https://youtube.com/@zamzamacademy/videos",
    "jrstudio": "https://youtube.com/@jrstudiomalayalam/videos",
    "raftalks": "https://youtube.com/@raftalksmalayalam/videos",
    "parvinder": "https://www.youtube.com/@pravindersheoran/videos",
    "qasimi": "https://www.youtube.com/@quranstudycentremukkam/videos",
    "sharique": "https://youtube.com/@shariquesamsudheen/videos",
    "drali": "https://youtube.com/@draligomaa/videos",
    "yaqeen": "https://youtube.com/@yaqeeninstituteofficial/videos",
    "talent": "https://youtube.com/@talentacademyonline/videos",
    "vijayakumarblathur": "https://youtube.com/@vijayakumarblathur/videos",
    "entridegree": "https://youtube.com/@entridegreelevelexams/videos",
    "suprabhatam": "https://youtube.com/@suprabhaatham2023/videos",
    "bayyinah": "https://youtube.com/@bayyinah/videos",
    "vallathorukatha": "https://www.youtube.com/@babu_ramachandran/videos",
    "furqan": "https://youtube.com/@alfurqan4991/videos",
    "skicr": "https://youtube.com/@skicrtv/videos",
    "dhruvrathee": "https://youtube.com/@dhruvrathee/videos",
    "safari": "https://youtube.com/@safaritvlive/videos",
    "sunnxt": "https://youtube.com/@sunnxtmalayalam/videos",
    "movieworld": "https://youtube.com/@movieworldmalayalammovies/videos",
    "comedy": "https://youtube.com/@malayalamcomedyscene5334/videos",
    "studyiq": "https://youtube.com/@studyiqiasenglish/videos",
"sreekanth": "https://youtube.com/@sreekanthvettiyar/videos",

"jr": "https://youtube.com/@yesitsmejr/videos",

"habib": "https://youtube.com/@habibomarcom/videos",

"unacademy": "https://youtube.com/@unacademyiasenglish/videos",

"eftguru": "https://youtube.com/@eftguru-ql8dk/videos",

"anurag": "https://youtube.com/@anuragtalks1/videos",



}

VIDEO_CACHE = {name: {"url": None, "last_checked": 0, "thumbnail": "", "upload_date": ""} for name in CHANNELS}
LAST_VIDEO_ID = {name: None for name in CHANNELS}
TMP_DIR = Path("/tmp/ytmp3")
TMP_DIR.mkdir(exist_ok=True)

def fetch_latest_video_url(name, channel_url):
    try:
        result = subprocess.run([
            "yt-dlp",
            "--dump-single-json",
            "--playlist-end", "1",
            "--cookies", "/mnt/data/cookies.txt",
            "--user-agent", FIXED_USER_AGENT,
            channel_url
        ], capture_output=True, text=True, check=True)

        data = json.loads(result.stdout)
        video = data["entries"][0]
        video_id = video["id"]
        thumbnail_url = video.get("thumbnail", "")
        upload_date = video.get("upload_date", "")
        video_title = video.get("title", "Unknown")
        return f"https://www.youtube.com/watch?v={video_id}", thumbnail_url, video_id, upload_date, video_title
    except Exception as e:
        logging.error(f"Error fetching video from {channel_url}: {e}")
        return None, None, None, None, None

def embed_thumbnail(mp3_path, thumbnail_url, video_title, channel_name):
    if not mp3_path.exists() or not thumbnail_url:
        return
    try:
        img_data = requests.get(thumbnail_url).content
        audio = MP3(mp3_path, ID3=ID3)
        try:
            audio.add_tags()
        except error:
            pass
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=img_data
            )
        )
        # Set Title, Album, and Artist tags
        audio.tags.add(TIT2(encoding=3, text=video_title))  # Title tag
        audio.tags.add(TALB(encoding=3, text=video_title))  # Album tag
        audio.tags.add(TPE1(encoding=3, text=channel_name))  # Artist tag
        audio.save()
        logging.info(f"Embedded thumbnail and metadata into {mp3_path}")
    except Exception as e:
        logging.error(f"Failed to embed thumbnail: {e}")

def download_and_convert(channel, video_url):
    final_path = TMP_DIR / f"{channel}.mp3"
    if final_path.exists():
        return final_path
    if not video_url:
        return None
    try:
        result = subprocess.run([
            "yt-dlp",
            "-f", "bestaudio",
            "--output", str(TMP_DIR / f"{channel}.%(ext)s"),
            "--cookies", "/mnt/data/cookies.txt",
            "--user-agent", FIXED_USER_AGENT,
            "--postprocessor-args", "-ar 22050 -ac 1 -b:a 40k",
            "--extract-audio",
            "--audio-format", "mp3",
            video_url
        ], check=True)
        # Embed thumbnail and metadata if available
        thumbnail_url = VIDEO_CACHE.get(channel, {}).get("thumbnail")
        video_title = VIDEO_CACHE.get(channel, {}).get("title", "Unknown Title")
        if thumbnail_url:
            embed_thumbnail(final_path, thumbnail_url, video_title, channel)
        return final_path if final_path.exists() else None
    except Exception as e:
        logging.error(f"Error converting {channel}: {e}")
        partial = final_path.with_suffix(".mp3.part")
        if partial.exists():
            partial.unlink()
        return None

def cleanup_old_files():
    while True:
        current_time = time.time()
        for file in TMP_DIR.glob("*.mp3"):
            if current_time - file.stat().st_mtime > EXPIRE_AGE:
                try:
                    logging.info(f"Cleaning up old file: {file}")
                    file.unlink()
                except Exception as e:
                    logging.error(f"Error cleaning up file {file}: {e}")
        time.sleep(EXPIRE_AGE)

def update_video_cache_loop():
    while True:
        for name, url in CHANNELS.items():
            video_url, thumbnail, video_id, upload_date = fetch_latest_video_url(name, url)
            if video_url and video_id:
                if LAST_VIDEO_ID[name] != video_id:
                    LAST_VIDEO_ID[name] = video_id
                    VIDEO_CACHE[name]["url"] = video_url
                    VIDEO_CACHE[name]["last_checked"] = time.time()
                    VIDEO_CACHE[name]["thumbnail"] = thumbnail
                    VIDEO_CACHE[name]["upload_date"] = upload_date
                    download_and_convert(name, video_url)
            time.sleep(3)
        time.sleep(REFRESH_INTERVAL)

def auto_download_mp3s():
    while True:
        for name, data in VIDEO_CACHE.items():
            video_url = data.get("url")
            if video_url:
                mp3_path = TMP_DIR / f"{name}.mp3"
                if not mp3_path.exists() or time.time() - mp3_path.stat().st_mtime > RECHECK_INTERVAL:
                    logging.info(f"Pre-downloading {name}")
                    download_and_convert(name, video_url)
            time.sleep(3)
        time.sleep(RECHECK_INTERVAL)

@app.route("/<channel>.mp3")
def stream_mp3(channel):
    if channel not in CHANNELS:
        return "Channel not found", 404

    video_url = VIDEO_CACHE[channel].get("url")
    upload_date = VIDEO_CACHE[channel].get("upload_date")
    if not video_url:
        video_url, thumbnail, video_id, upload_date = fetch_latest_video_url(channel, CHANNELS[channel])
        if not video_url:
            return "Unable to fetch video", 500
        if video_id and LAST_VIDEO_ID[channel] != video_id:
            LAST_VIDEO_ID[channel] = video_id
            VIDEO_CACHE[channel]["url"] = video_url
            VIDEO_CACHE[channel]["thumbnail"] = thumbnail
            VIDEO_CACHE[channel]["upload_date"] = upload_date
            VIDEO_CACHE[channel]["last_checked"] = time.time()

    mp3_path = download_and_convert(channel, video_url)
    if not mp3_path or not mp3_path.exists():
        return "Error preparing stream", 500

    file_size = os.path.getsize(mp3_path)
    range_header = request.headers.get('Range', None)
    headers = {
        'Content-Type': 'audio/mpeg',
        'Accept-Ranges': 'bytes',
    }

    if range_header:
        try:
            range_value = range_header.strip().split("=")[1]
            byte1, byte2 = range_value.split("-")
            byte1 = int(byte1)
            byte2 = int(byte2) if byte2 else file_size - 1
        except Exception as e:
            return f"Invalid Range header: {e}", 400

        length = byte2 - byte1 + 1
        with open(mp3_path, 'rb') as f:
            f.seek(byte1)
            chunk = f.read(length)

        headers.update({
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Content-Length': str(length)
        })
        return Response(chunk, status=206, headers=headers)

    with open(mp3_path, 'rb') as f:
        data = f.read()
    headers['Content-Length'] = str(file_size)
    return Response(data, headers=headers)

@app.route("/thumb/<channel>.jpg")
def thumb(channel):
    """Serve the thumbnail image as proxy"""
    if channel not in CHANNELS:
        return "Channel not found", 404

    thumbnail_url = VIDEO_CACHE[channel].get("thumbnail", "")
    if not thumbnail_url:
        thumbnail_url = "https://via.placeholder.com/320x180?text=No+Thumbnail"

    try:
        r = requests.get(thumbnail_url, headers={"User-Agent": FIXED_USER_AGENT}, timeout=5)
        return Response(r.content, content_type="image/jpeg")
    except Exception as e:
        logging.error(f"Error fetching thumbnail for {channel}: {e}")
        return "Error loading thumbnail", 500

@app.route("/")
def index():
    html = """
    <html><head><title>YouTube Mp3</title></head>
    <body style="font-family:sans-serif; font-size:12px; background:#fff;">
    <h3>YouTube Mp3</h3>
    """
    def get_upload_date(channel):
        return VIDEO_CACHE[channel].get("upload_date", "Unknown")

    for channel in sorted(CHANNELS, key=lambda x: get_upload_date(x), reverse=True):
        mp3_path = TMP_DIR / f"{channel}.mp3"
        if not mp3_path.exists():
            continue

        upload_date = get_upload_date(channel)
        html += f"""
        <div style="margin-bottom:10px;">
            <img src="/thumb/{channel}.jpg" style="width:160px;height:90px;object-fit:cover;">
            <br>
            <a href="/{channel}.mp3">{channel} ({upload_date})</a>
        </div>
        """

    html += "</body></html>"
    return html

# Start background tasks
threading.Thread(target=update_video_cache_loop, daemon=True).start()
threading.Thread(target=auto_download_mp3s, daemon=True).start()
threading.Thread(target=cleanup_old_files, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)