# Use a lightweight Python base image
FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Install FFmpeg with only necessary dependencies
RUN apt update && apt install -y --no-install-recommends \
    ffmpeg \
    libssl-dev && \
    apt clean && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask port
EXPOSE 5000

# Run the streaming script
CMD ["python", "stream.py"]