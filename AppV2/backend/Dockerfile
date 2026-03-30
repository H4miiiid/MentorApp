FROM python:3.13-slim

# Docker CLI for sandboxed student code execution (uses host socket from compose).
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ENV APPV2_HOST=0.0.0.0 \
    APPV2_PORT=8001 \
    APPV2_DB_PATH=/data/mentorapp_v2.db \
    APPV2_STORAGE_DIR=/data/storage
# Set at runtime (e.g. docker compose): APPV2_JWT_SECRET — HS256 signing key for access tokens
ENV APPV2_JWT_SECRET=

COPY AppV2/backend/requirements.txt /app/AppV2/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/AppV2/backend/requirements.txt

COPY AppV2/backend /app/AppV2/backend

EXPOSE 8001

# --log-level info: align uvicorn with app logging; grading logs use AppV2.backend.* loggers to stdout
CMD ["sh", "-c", "exec uvicorn AppV2.backend.main:app --host \"${APPV2_HOST}\" --port \"${APPV2_PORT}\" --log-level info"]
