from flask import Flask, request, Response
import subprocess

app = Flask(__name__)

CHANNELS = {
    "gtrk_volga": "https://gtrk-volga.ru/media/hr24/stream1.m3u8"
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
            "-user_agent", "Mozilla/5.0",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "2",
            "-i", stream_url,
            "-vf", "scale=176:144",
            "-vcodec", "h263",
            "-b:v", "70k",
            "-r", "15",
            "-acodec", "libopencore_amrnb",
            "-ar", "8000",
            "-ac", "1",
            "-f", "3gp",
            "pipe:1"
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**5)

        # Optional: log stderr for debugging
        for line in process.stderr:
            print(line.decode('utf-8'), end='')

        try:
            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                yield chunk
        finally:
            process.kill()

    return Response(generate(), content_type="video/3gp")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)