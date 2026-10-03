ARG PYTHON_VERSION=3.14.7
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt requirements.lock .
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_CACHE_DIR=0 pip install --require-hashes -r requirements.lock


FROM builder AS test-deps

COPY requirements-dev.txt requirements-dev.lock .
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_CACHE_DIR=0 pip install --require-hashes -r requirements-dev.lock


FROM python:${PYTHON_VERSION}-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-dejavu-core \
        fonts-noto-color-emoji \
        gosu \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 sirius \
    && useradd --uid 10001 --gid sirius --no-create-home --shell /usr/sbin/nologin sirius

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY docker/entrypoint.sh /usr/local/bin/sirius-entrypoint

RUN chmod 0755 /usr/local/bin/sirius-entrypoint \
    && mkdir -p /app/data /app/logs /app/sessions \
    && chown -R sirius:sirius /app/data /app/logs /app/sessions

COPY --chown=sirius:sirius requirements.txt alembic.ini main.py ./
COPY --chown=sirius:sirius bot ./bot
COPY --chown=sirius:sirius core ./core
COPY --chown=sirius:sirius db ./db
COPY --chown=sirius:sirius locales ./locales
COPY --chown=sirius:sirius migrations ./migrations
COPY --chown=sirius:sirius ml ./ml
COPY --chown=sirius:sirius services ./services
COPY --chown=sirius:sirius userbot ./userbot
COPY --chown=sirius:sirius utils ./utils
COPY --chown=sirius:sirius workers ./workers

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; port = os.environ.get('HEALTH_PORT', '8080'); urllib.request.urlopen(f'http://127.0.0.1:{port}/ready', timeout=3).read()"]

# The entrypoint needs root only to align bind-mount ownership; it immediately
# execs the requested process as uid/gid 10001.
ENTRYPOINT ["/usr/local/bin/sirius-entrypoint"]
CMD ["python", "-m", "main"]


FROM runtime-base AS test

USER root
COPY --from=test-deps /opt/venv /opt/venv
COPY --chown=sirius:sirius requirements-dev.txt pytest.ini ./
COPY --chown=sirius:sirius tests ./tests
COPY --chown=sirius:sirius scripts/ui_preview.py ./scripts/ui_preview.py

USER sirius
ENTRYPOINT []
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


FROM runtime-base AS runtime
