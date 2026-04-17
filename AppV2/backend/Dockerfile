FROM python:3.13-slim

# Docker CLI for sandboxed student code execution (talks to host daemon via the
# socket mounted in docker-compose.yml). We install the static CLI from Docker's
# official CDN instead of relying on Debian's `docker.io` package, because on
# Debian 13 "trixie" that package was split and no longer ships the `docker`
# client binary — only the daemon. Pinning a static tarball works on every
# Debian/Ubuntu base and avoids a whole apt-repo setup.
ARG DOCKER_CLI_VERSION=27.4.1
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl; \
    rm -rf /var/lib/apt/lists/*; \
    arch="$(uname -m)"; \
    case "$arch" in \
      x86_64)   static_arch="x86_64" ;; \
      aarch64)  static_arch="aarch64" ;; \
      *)        echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${static_arch}/docker-${DOCKER_CLI_VERSION}.tgz" -o /tmp/docker.tgz; \
    tar -xzf /tmp/docker.tgz -C /tmp; \
    install -m 0755 /tmp/docker/docker /usr/local/bin/docker; \
    rm -rf /tmp/docker /tmp/docker.tgz; \
    # Fail the build early if the CLI is missing or non-functional.
    docker --version

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
