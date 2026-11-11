# syntax=docker/dockerfile:1.4
FROM python:3.13-slim

LABEL maintainer="Ricardo M. (@Moztoo)"
LABEL description="BBVA México Fondos de Inversión Home Assistant App"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY openapi.json /app/openapi.json
COPY run.sh /app/run.sh

RUN chmod +x /app/run.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8088 \
    DATABASE_PATH=/data/bbva_fondos.db

EXPOSE 8088

CMD ["/app/run.sh"]
