# syntax=docker/dockerfile:1.4
# Stage 1: Build & Dependencies
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime image
FROM python:3.13-slim AS runtime

LABEL maintainer="Ricardo M. (@ricardom)"
LABEL description="BBVA México Fondos de Inversión Scraper, Database, REST API and Dashboard"

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appgroup /app

# Copy application code
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup openapi.json /app/openapi.json

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8088 \
    DATABASE_PATH=/app/data/bbva_fondos.db

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/api/v1/health', timeout=4)" || exit 1

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
