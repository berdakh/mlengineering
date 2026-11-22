# syntax=docker/dockerfile:1
# flowguard prediction API, reproducible multi-stage build - REFERENCE SOLUTION (w6d2).
#   docker build --build-arg REVISION="$(git rev-parse --short HEAD)" -t flowguard:0.6.0 .

# The base image is pinned by DIGEST (the multi-arch index of python:3.12-slim on 2026-11-22).
# A tag such as 3.12-slim moves when Debian or Python patch releases ship; a digest never does.
# To update it on purpose:  docker buildx imagetools inspect python:3.12-slim
ARG PYTHON_BASE=python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

# ---------- stage 1: resolve and install dependencies into a virtual environment ----------
FROM ${PYTHON_BASE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
# A venv without pip: the runtime image will not be able to install anything.
RUN python -m venv --without-pip /opt/venv
COPY requirements.lock /tmp/requirements.lock
# Hash-checking mode: every package, transitive ones included, must be pinned with == and match
# one of the listed sha256 hashes, or pip refuses to install anything.
RUN pip --python /opt/venv/bin/python install --require-hashes -r /tmp/requirements.lock

# ---------- stage 2: the runtime image: base + venv + code + model, nothing else ----------
FROM ${PYTHON_BASE} AS runtime
ARG VERSION=0.6.0
ARG REVISION=unknown
LABEL org.opencontainers.image.title="flowguard" \
      org.opencontainers.image.description="SKAB fault-score API (educational prototype)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src \
    FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0

COPY --from=builder /opt/venv /opt/venv
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY src/ ./src/
COPY models/ ./models/

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
