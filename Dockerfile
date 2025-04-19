# Use Python 3.12 slim image as the base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install yt-dlp from the latest release
RUN wget -O /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Copy the application code into the container
COPY . /app

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create a persistent storage path (Koyeb will mount this at runtime)
VOLUME /mnt/data

# Expose port 8000 for the Flask application
EXPOSE 8000

# Command to run the app
CMD ["python", "restream.py"]