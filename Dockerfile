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

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables (example, modify as needed)
ENV FLASK_APP=app.py

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]