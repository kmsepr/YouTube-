FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install yt-dlp
RUN wget -O /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Copy app code
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create persistent storage path (Koyeb will mount it at runtime)
VOLUME /mnt/data

EXPOSE 8000

CMD ["python", "restream.py"]