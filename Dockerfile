# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for FFmpeg and building from source
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    yasm \
    pkg-config \
    wget \
    libx264-dev \
    libvpx-dev \
    libfreetype6-dev \
    libmp3lame-dev \
    libopus-dev \
    libssl-dev \
    autoconf \
    libxml2-dev \
    && \
    # Download and install libfdk-aac from source
    wget https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v2.0.2.tar.gz && \
    tar -xzvf v2.0.2.tar.gz && \
    cd fdk-aac-2.0.2 && \
    autoreconf -fiv && \
    ./configure --enable-shared && \
    make && \
    make install && \
    cd .. && \
    rm -rf fdk-aac-2.0.2 v2.0.2.tar.gz && \
    # Install FFmpeg from source with required flags
    wget https://ffmpeg.org/releases/ffmpeg-4.4.tar.bz2 && \
    tar -xjf ffmpeg-4.4.tar.bz2 && \
    cd ffmpeg-4.4 && \
    ./configure --enable-gpl --enable-nonfree --enable-libfdk-aac --enable-libx264 --enable-libvpx --enable-libmp3lame --enable-libopus --enable-libfreetype --enable-libxml2 --enable-openssl --enable-version3 && \
    make && \
    make install && \
    cd .. && \
    rm -rf /var/lib/apt/lists/* /ffmpeg-4.4.tar.bz2 /ffmpeg-4.4

# Install Flask and any Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app into the container
COPY . /app/

# Expose the port the app runs on
EXPOSE 8080

# Command to run the app
CMD ["python", "stream.py"]