Use a lightweight base image with Python

FROM python:3.11-slim

Install system dependencies

RUN apt-get update && apt-get install -y 
ffmpeg 
curl 
wget 
git 
gcc 
libmagic-dev 
&& rm -rf /var/lib/apt/lists/*

Set work directory

WORKDIR /app

Install Python dependencies

COPY requirements.txt . RUN pip install --no-cache-dir -r requirements.txt

Copy app files

COPY . .

Download latest yt-dlp

RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && 
chmod a+rx /usr/local/bin/yt-dlp

Expose port

EXPOSE 8080

Run the app

CMD ["python", "restream.py"]

