from flask import Flask, request, Response
import subprocess

app = Flask(__name__)

CHANNELS = {
    "safari_tv": "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "victers_tv": "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/victers/tv1/chunks.m3u8",
    "kairali_we": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/wetv_nim_https/050522/wetv/playlist.m3u8",
    "flowers_tv": "http://103.199.161.254/Content/flowers/Live/Channel(Flowers)/index.m3u8",
    "dd_malayalam": "https://d3eyhgoylams0m.cloudfront.net/v1/manifest/93ce20f0f52760bf38be911ff4c91ed02aa2fd92/ed7bd2c7-8d10-4051-b397-2f6b90f99acb/562ee8f9-9950-48a0-ba1d-effa00cf0478/2.m3u8",
    "amrita_tv": "https://dr1zhpsuem5f4.cloudfront.net/master.m3u8",
    "24_news": "https://segment.yuppcdn.net/110322/channel24/playlist.m3u8",
    "mazhavil_manorama": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8",
    "manorama_news": "http://103.199.161.254/Content/manoramanews/Live/Channel(ManoramaNews)/index.m3u8",
    "aaj_tak": "https://feeds.intoday.in/aajtak/api/aajtakhd/master.m3u8",
    "bloomberg_tv": "https://bloomberg-bloomberg-3-br.samsung.wurl.tv/manifest/playlist.m3u8"
}

@app.route("/stream")
def stream():
    # Get channel name from the URL query string
    channel = request.args.get("channel")

    # Check if the channel exists
    if channel not in CHANNELS:
        return "Invalid channel", 400

    stream_url = CHANNELS[channel]

    # Function to generate the video stream
    def generate():
        command = [
            "ffmpeg", "-re", "-i", stream_url,
            "-c:v", "h263", "-b:v", "70k", "-r", "15", "-vf", "scale=176:144",  # Video transcoding
            "-c:a", "aac", "-b:a", "32k", "-ac", "1", "-ar", "16000",  # Audio transcoding
            "-f", "3gp",  # Output container format
            "pipe:1"  # Output to stdout
        ]

        # Start the FFmpeg process
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        try:
            # Continuously read the output stream from FFmpeg
            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                yield chunk
        finally:
            # Make sure the FFmpeg process is terminated
            process.terminate()

    # Return the video stream as an HTTP response with the proper content type
    return Response(generate(), content_type="video/3gp")

if __name__ == "__main__":
    # Run the Flask application
    app.run(host="0.0.0.0", port=8080, threaded=True)