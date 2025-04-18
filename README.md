
*YouTube Audio Streamer*

A lightweight Flask application that streams audio (MP3) from the most recent uploaded video of selected YouTube channels using yt-dlp and ffmpeg.

This project is ideal for creating low-bandwidth audio streams from YouTube content — particularly useful for older devices (like Symbian phones with CorePlayer) or embedded use-cases.


---

Features

Streams audio from the latest uploaded video (not live streams)

Audio is transcoded to MP3 (mono, 64 kbps) using ffmpeg

Automatically refreshes every 30 minutes

Supports multiple channels via simple route pattern (/channel_name.mp3)

Optimized for use on older phones, embedded devices, or minimal players



---

Example

If you have a channel like:

"skicr": "https://www.youtube.com/@skicrtv/videos"

Then this will be accessible via:

http://your-server/skicr.mp3

The app will serve the MP3 stream from the most recently uploaded video on that channel.


---

Installation

1. Clone the repository

git clone https://github.com/yourusername/youtube-audio-streamer.git
cd youtube-audio-streamer


2. Install dependencies

pip install flask


3. Install yt-dlp and ffmpeg


4. Add your cookies.txt file (optional but recommended for age-restricted/private videos):

Place it at: /mnt/data/cookies.txt (or change the path in the code)


5. Run the app

python app.py




---

Customization

Add or remove channels in the CHANNELS dictionary in the script:

CHANNELS = {
    "skicr": "https://www.youtube.com/@skicrtv/videos",
    "ddm": "https://www.youtube.com/@ddmalayalamtv/videos",
    "furqan": "https://www.youtube.com/@alfurqan4991/videos",
    ...
}

Each channel will be accessible at /channel_name.mp3.


---

License

This project is licensed under the MIT License. You are free to use, modify, and distribute it.


