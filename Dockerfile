FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y ffmpeg && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENV FLASK_APP=restream.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8000

CMD ["flask", "run"]