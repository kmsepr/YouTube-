from flask import Flask, Response, request
import subprocess

app = Flask(__name__)

# IPTV Channel List
channels = {
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/victers/tv1/chunks.m3u8",
    "flowers_tv": "http://103.199.161.254/Content/flowers/Live/Channel(Flowers)/index.m3u8",
    "manorama_news": "http://103.199.161.254/Content/manoramanews/Live/Channel(ManoramaNews)/index.m3u8",
    "aaj_tak": "https://feeds.intoday.in/aajtak/api/aajtakhd/master.m3u8"
}

@app.route('/')
def index():
    return '''
        <h2>Available IPTV Channels</h2>
        <ul>
            <li><a href="/stream?channel=safari_tv">Safari TV</a></li>
            <li><a href="/stream?channel=victers_tv">Victers TV</a></li>
            <li><a href="/stream?channel=flowers_tv">Flowers TV</a></li>
            <li><a href="/stream?channel=manorama_news">Manorama News</a></li>
            <li><a href="/stream?channel=aaj_tak">Aaj Tak</a></li>
        </ul>
    '''

@app.route('/stream')
def stream():
    channel = request.args.get('channel')
    if not channel or channel not in channels:
        return "Invalid channel!", 400

    url = channels[channel]

    ffmpeg_command = [
        'ffmpeg',
        '-i', url,
        '-map', '0:v:0',
        '-map', '0:a:0',
        '-acodec', 'amr_wb',
        '-ar', '16000',
        '-ac', '1',
        '-vcodec', 'h263',
        '-vb', '70k',
        '-r', '15',
        '-vf', 'scale=176:144',
        '-f', '3gp',
        '-movflags', 'frag_keyframe+empty_moov',
        'pipe:1'
    ]

    def generate():
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            chunk = process.stdout.read(1024)
            if not chunk:
                break
            yield chunk

    return Response(generate(), content_type='video/3gpp')

if __name__ == '__main__':
    app.run(debug=True, host='0