# Use an official base image
FROM ubuntu:20.04

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and tools for building FFmpeg and fdk-aac
RUN apt-get update && apt-get install -y \
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
    autoconf \               # Install autoconf (for autoreconf)
    && rm -rf /var/lib/apt/lists/*

# Download and build fdk-aac
RUN wget https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v2.0.2.tar.gz && \
    tar -xzvf v2.0.2.tar.gz && \
    cd fdk-aac-2.0.2 && \
    autoreconf -fiv && \
    ./configure --enable-shared && \
    make && \
    make install && \
    cd .. && \
    rm -rf fdk-aac-2.0.2 v2.0.2.tar.gz

# Download and build FFmpeg
RUN wget https://ffmpeg.org/releases/ffmpeg-4.4.tar.bz2 && \
    tar -xjf ffmpeg-4.4.tar.bz2 && \
    cd ffmpeg-4.4 && \
    ./configure --enable-gpl --enable-nonfree --enable-libfdk-aac --enable-libx264 --enable-libvpx --enable-libmp3lame --enable-libopus --enable-libfreetype --enable-amr-wb && \
    make && \
    make install && \
    cd .. && \
    rm -rf /ffmpeg-4.4.tar.bz2

# Set the default command
CMD ["ffmpeg", "-version"]