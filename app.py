from flask import Flask, Response, request
import subprocess
import os

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
    # Simple home page listing the available channels
    return '''
        <h2>Click a Channel to Play</h2>
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
    # Get the requested channel from the URL
    channel = request.args.get('channel')

    # Check if the requested channel exists in the list
    if not channel or channel not in channels:
        return "Invalid channel! Please choose a valid channel.", 400

    # Get the M3U8 stream URL for the selected channel
    url = channels[channel]

    # Set the FFmpeg command to stream the video as 3GP
    ffmpeg_command = [
        'ffmpeg',
        '-i', url,                           # Input URL (M3U8)
        '-map', '0:v:0',                      # Video stream
        '-map', '0:a:0',                      # Audio stream
        '-acodec', 'amr_wb',                  # AMR-WB codec for audio
        '-ar', '16000',                       # Audio sampling rate
        '-ac', '1',                           # Mono audio channel
        '-vcodec', 'h263',                    # H.263 video codec
        '-vb', '70k',                         # Video bitrate
        '-r', '15',                           # Frame rate
        '-vf', 'scale=176:144',               # Video resolution
        '-f', '3gp',                          # Output format: 3GP
        '-movflags', 'frag_keyframe+empty_moov', # Fragment the file for better streaming
        'pipe:1'                              # Output to stdout (streaming)
    ]

    # Use subprocess to run FFmpeg and capture the output to stream to the browser
    def generate():
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            # Read the output from FFmpeg and yield it as a response chunk
            chunk = process.stdout.read(1024)
            if not chunk:
                break
            yield chunk

        # Check for errors in FFmpeg execution
        stderr = process.stderr.read().decode()
        if stderr:
            print(f"FFmpeg error: {stderr}")
            return "An error occurred while processing the stream.", 500

    # Set the correct content-type for the 3GP video stream
    return Response(generate(), content_type='video/3gpp')

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)