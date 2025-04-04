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
            "-timeout", "1000000",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "2",
            "-re",  # Real-time simulation
            "-i", stream_url,
            "-acodec", "amr_wb",
            "-ar", "16000",
            "-ac", "1",
            "-vcodec", "h263",
            "-vb", "70k",
            "-r", "15",
            "-vf", "scale=176:144",
            "-f", "3gp",
            "pipe:1"
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

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