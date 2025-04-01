# Use an official Ubuntu base image
FROM ubuntu:20.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
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
    libvo-amrwbenc-dev \
    git \
    && apt-get clean

# Download and install libfdk-aac
RUN wget https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v2.0.2.tar.gz && \
    tar -xzvf v2.0.2.tar.gz && \
    cd fdk-aac-2.0.2 && \
    autoreconf -fiv && \
    ./configure --enable-shared && \
    make && \
    make install && \
    cd .. && \
    rm -rf fdk-aac-2.0.2 v2.0.2.tar.gz

# Install FFmpeg from source
RUN wget https://ffmpeg.org/releases/ffmpeg-4.4.tar.bz2 && \
    tar -xjf ffmpeg-4.4.tar.bz2 && \
    cd ffmpeg-4.4 && \
    ./configure --enable-gpl \
                --enable-nonfree \
                --enable-libfdk-aac \
                --enable-libx264 \
                --enable-libvpx \
                --enable-libmp3lame \
                --enable-libopus \
                --enable-libfreetype \
                --enable-libxml2 \
                --enable-openssl \
                --enable-version3 \
                --enable-libvo-amrwbenc && \
    make && \
    make install && \
    cd .. && \
    rm -rf ffmpeg-4.4.tar.bz2 ffmpeg-4.4

# Clean up unnecessary apt cache
RUN rm -rf /var/lib/apt/lists/*

# Expose the port for streaming
EXPOSE 80

# Command to keep the container running (this could be adjusted depending on your use case)
CMD ["tail", "-f", "/dev/null"]