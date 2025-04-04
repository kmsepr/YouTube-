# Use Python slim base
FROM python:3.10-slim

# Environment variable to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install FFmpeg with AMR-NB support and other dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopencore-amrnb0 \
    libxml2-dev \
    libssl-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app
COPY stream.py /app/

# Expose port
EXPOSE 8080

# Run the app
CMD ["python", "stream.py"]