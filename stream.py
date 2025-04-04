from flask import Flask, request, Response
import subprocess

app = Flask(__name__)

CHANNELS = {
    "kairali_we": "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/wetv_nim_https/050522/wetv/playlist.m3u8"
}

@app.route("/stream")
def stream():
    channel = request.args.get("channel")

    if channel not in CHANNELS:
        return "Invalid channel", 400

    stream_url = CHANNELS[channel]

    def generate():
        command = [
            "ffmpeg",
            "-re",  # simulate real-time input
            "-i", stream_url,
            "-vf", "scale=176:144",
            "-c:v", "h263",
            "-b:v", "128k",
            "-r", "15",
            "-c:a", "aac",
            "-b:a", "32k",
            "-ac", "1",
            "-ar", "8000",
            "-f", "3gp",
            "pipe:1"
        ]

        # Start FFmpeg and capture both stdout and stderr
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                yield chunk
        finally:
            process.terminate()

    return Response(generate(), content_type="video/3gp")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)