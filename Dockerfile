# Use Python 3.8 as the base image
FROM python:3.8-slim

# Install FFmpeg and dependencies
RUN apt update && apt install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the Python script into the container
COPY app.py /app/app.py

# Install required Python libraries
RUN pip install --no-cache-dir Flask

# Expose port 5000 for the Flask app
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "app.py"]