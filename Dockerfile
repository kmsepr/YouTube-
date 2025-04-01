# Use Python 3.8-slim as the base image
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install required dependencies for FFmpeg (excluding libfdk-aac-dev)
RUN apt update && apt install -y \
    build-essential \
    yasm \
    libtool \
    libssl-dev \
    libxml2-dev \
    libvo-amrwbenc-dev \
    pkg-config \
    libx264-dev \
    libmp3lame-dev && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY . .

# Install Python dependencies (add requirements.txt if needed)
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on (if you're using Flask)
EXPOSE 5000

# Run the streaming script directly
CMD ["python", "stream.py"]