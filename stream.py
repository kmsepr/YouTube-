from flask import Flask, Response
import subprocess

app = Flask(__name__)

@app.route("/stream")
def stream():
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/wetv_nim_https/050522/wetv/playlist.m3u8",
        "-vf", "scale=176:144",
        "-c:v", "h263",
        "-b:v", "128k",
        "-c:a", "aac",
        "-b:a", "32k",
        "-ar", "8000",
        "-f", "3gp",
        "pipe:1"
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

    def generate():
        while True:
            chunk = process.stdout.read(1024)  # Read 1KB chunks
            if not chunk:
                break
            yield chunk

    headers = {
    "Content-Type": "application/sdp"
}
    return Response(generate(), headers=headers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)