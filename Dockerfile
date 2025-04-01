# Use Python 3.8-slim as the base image
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install required dependencies for FFmpeg
RUN apt update && apt install -y \
    build-essential \
    yasm \
    libtool \
    libssl-dev \
    libxml2-dev \
    libvo-amrwbenc-dev \
    pkg-config \
    libx264-dev \
    libmp3lame-dev \
    ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on (Flask default port)
EXPOSE 5000

# Run the streaming script directly
CMD ["python", "stream.py"]