# Cloud Run / local Docker image for FastAPI + YOLOv8n inference (CPU).
# Train locally; copy best.pt into backend/model/ before building.

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    SERIAL_ENABLED=false \
    HOST=0.0.0.0

WORKDIR /app

# System libs for OpenCV / torch CPU wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Fail the build early if weights are missing
RUN test -f model/best.pt || (echo "ERROR: model/best.pt missing. Train locally first." && exit 1)

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
