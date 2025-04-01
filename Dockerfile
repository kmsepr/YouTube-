# Use a Python base image
FROM python:3.10-slim

# Set environment variables for non-interactive installations
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libxml2-dev \
    libssl-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy the stream.py to the container
COPY stream.py /app/

# Expose port for the Flask app
EXPOSE 8080

# Set the default command to run the Flask app
CMD ["python", "stream.py"]