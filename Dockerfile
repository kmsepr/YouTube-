FROM python:3.12-slim

WORKDIR /app

COPY . /app

# Install ffmpeg and other dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["python", "restream.py"]