# Use Python 3.8 as the base image
FROM python:3.8-slim

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
    libfdk-aac-dev \
    libmp3lame-dev && rm -rf /var/lib/apt/lists/*

# Download and compile FFmpeg
RUN git clone https://git.ffmpeg.org/ffmpeg.git /ffmpeg && \
    cd /ffmpeg && \
    ./configure \
        --prefix=/usr/local/ffmpeg \
        --enable-libvo-amrwbenc \
        --enable-libxml2 \
        --enable-openssl \
        --enable-version3 \
        --enable-gpl \
        --enable-nonfree \
        --enable-libx264 \
        --enable-fdk-aac \
        --enable-libmp3lame && \
    make -j$(nproc) && \
    make install

# Set the environment variable to make the compiled FFmpeg available
ENV PATH="/usr/local/ffmpeg/bin:${PATH}"

# Install Python libraries
RUN pip install --no-cache-dir Flask

# Set working directory
WORKDIR /app

# Copy Python script into the container
COPY app.py /app/app.py

# Expose port for Flask app
EXPOSE 5000

# Command to run Flask app
CMD ["python", "app.py"]