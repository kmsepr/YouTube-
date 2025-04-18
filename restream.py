from flask import Flask, Response, request, jsonify import subprocess import json import os import time import logging

app = Flask(name) logging.basicConfig(level=logging.INFO)

🔐 Optional token protection (set ACCESS_TOKEN in env to enable)

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", None)

🎯 Station configuration: map station keys to YouTube channel URLs

STATIONS = { "safari_tv": "https://www.youtube.com/@safaritvlive/videos", "babu_ramachandran": "https://www.youtube.com/@babu_ramachandran/videos" }

📂 Cookies file for yt-dlp

COOKIES_FILE = "/mnt/data/cookies.txt"

⏱ Cache TTL in seconds

CACHE_TTL = 1800  # 30 minutes

🗄 In-memory cache: station -> {"timestamp": float, "urls": list}

CACHE = {}

Number of latest videos to include per station

PLAYLIST_LENGTH = 5

@app.before_request def require_token(): if ACCESS_TOKEN: token = request.args.get("token") if token != ACCESS_TOKEN: return "Unauthorized", 403

def fetch_latest_urls(station): """Fetch latest PLAYLIST_LENGTH video URLs for the given station.""" channel_url = STATIONS[station] cmd = [ "yt-dlp", "--flat-playlist", "--dump-json", f"--playlist-end {PLAYLIST_LENGTH}", channel_url ] result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True) if result.returncode != 0: logging.error(f"Failed to fetch playlist for {station}: {result.stderr}") return []

urls = []
for line in result.stdout.splitlines():
    try:
        info = json.loads(line)
        vid = info.get("id")
        if vid:
            urls.append(f"https://www.youtube.com/watch?v={vid}")
    except json.JSONDecodeError:
        continue
return urls

def get_cached_urls(station): """Return cached URLs if fresh; otherwise fetch and cache.""" now = time.time() entry = CACHE.get(station) if entry and now - entry['timestamp'] < CACHE_TTL: return entry['urls']

urls = fetch_latest_urls(station)
if urls:
    CACHE[station] = { 'timestamp': now, 'urls': urls }
return urls

def generate_stream(urls): """Generate a continuous MP3 stream from a list of URLs.""" while True: for video_url in urls: logging.info(f"Streaming {video_url}") ytdlp_cmd = [ "yt-dlp", "--cookies", COOKIES_FILE, "--add-header", "User-Agent: Mozilla/5.0", "--add-header", "Accept-Language: en-US,en;q=0.5", "-f", "bestaudio[ext=m4a]/bestaudio", "-o", "-", video_url ] ffmpeg_cmd = [ "ffmpeg", "-re", "-i", "pipe:0", "-vn", "-acodec", "libmp3lame", "-f", "mp3", "pipe:1" ]

ytdlp = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE)
        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=ytdlp.stdout, stdout=subprocess.PIPE)

        try:
            for chunk in iter(lambda: ffmpeg.stdout.read(4096), b""):
                yield chunk
        except GeneratorExit:
            break
        finally:
            for p in (ytdlp, ffmpeg):
                try:
                    p.kill()
                except:
                    pass
    # After looping through URLs, refresh cache
    urls = get_cached_urls(station)
    if not urls:
        logging.warning(f"No URLs for {station}, retrying in 30s")
        time.sleep(30)

@app.route("/stations") def list_stations(): return jsonify({ 'stations': list(STATIONS.keys()) })

@app.route("/<station>/stream.mp3") def stream_mp3(station): if station not in STATIONS: return "Station not found", 404 urls = get_cached_urls(station) if not urls: return "Unable to fetch streams", 503 return Response(generate_stream(urls), mimetype="audio/mpeg")

@app.route("/<station>.m3u") def playlist_m3u(station): if station not in STATIONS: return "Station not found", 404 host = request.host token_qs = f"?token={ACCESS_TOKEN}" if ACCESS_TOKEN else "" url = f"http://{host}/{station}/stream.mp3{token_qs}" m3u = f"#EXTM3U\n#EXTINF:-1,{station}\n{url}\n" return Response(m3u, mimetype="audio/x-mpegurl")

@app.route("/health") def health(): return "OK", 200

@app.route("/") def index(): host = request.host token_qs = f"?token={ACCESS_TOKEN}" if ACCESS_TOKEN else "" items = [] for s in STATIONS: items.append(f'<li><a href="/{s}/stream.mp3{token_qs}">{s} Stream</a></li>') items.append(f'<li><a href="/{s}.m3u{token_qs}">{s} Playlist</a></li>') return f"<h2>Available Stations</h2><ul>{''.join(items)}</ul>"

if name == "main": port = int(os.environ.get("PORT", 8000)) app.run(host="0.0.0.0", port=port)

