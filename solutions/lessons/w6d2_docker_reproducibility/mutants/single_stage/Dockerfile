# syntax=docker/dockerfile:1
ARG PYTHON_BASE=python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
FROM ${PYTHON_BASE}
ARG VERSION=0.6.0
ARG REVISION=unknown
LABEL org.opencontainers.image.version="${VERSION}" org.opencontainers.image.revision="${REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0
WORKDIR /app
COPY requirements.lock .
RUN pip install --require-hashes -r requirements.lock
COPY src/ ./src/
COPY models/ ./models/
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app
USER app
EXPOSE 8000
HEALTHCHECK CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
