

# YouTube Audio Streamer

A lightweight Flask application that streams audio (MP3) from the most recent uploaded video of selected YouTube channels using `yt-dlp` and `ffmpeg`.

Perfect for low-bandwidth audio access to YouTube content — especially useful for older devices (like Symbian phones with CorePlayer) or embedded systems.

---

### Features

- Streams audio from the latest uploaded video (not live)
- Transcodes audio to MP3 (mono, 40 kbps) using `ffmpeg`
- Automatically refreshes every 30 minutes
- Simple route pattern: `/channel_name.mp3`
- Optimized for older phones and minimal media players

---

### Example Use

If you define a channel like:

```python
CHANNELS = {
    "skicr": "https://www.youtube.com/@skicrtv/videos"
}

You can stream it from:

http://your-server/skicr.mp3

This returns the MP3 stream of the most recently uploaded video from that channel.


---

Setup Instructions

1. Clone the repository

git clone https://github.com/yourusername/youtube-audio-streamer.git
cd youtube-audio-streamer

2. Install dependencies

pip install flask

3. Install yt-dlp and ffmpeg

Ensure both are available in your $PATH.

4. (Optional) Add cookies.txt

For age-restricted/private content, place cookies.txt at:

/mnt/data/cookies.txt

Or change the path in your script.

5. Run the app

python app.py

The app will be available at:

http://localhost:8000


---

Customization

Edit the CHANNELS dictionary in the script:

CHANNELS = {
    "skicr": "https://www.youtube.com/@skicrtv/videos",
    "ddm": "https://www.youtube.com/@ddmalayalamtv/videos",
    "furqan": "https://www.youtube.com/@alfurqan4991/videos",
    ...
}

Each will be accessible via /channel_name.mp3.


---

License

This project is licensed under the MIT License. Use it freely and modify as needed.

