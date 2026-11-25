# syntax=docker/dockerfile:1
# flowguard prediction API - REFERENCE SOLUTION (w6d1). Build from this directory:
#   docker build -t flowguard:0.6.0 .
FROM python:3.12-slim

# No .pyc files in the image, unbuffered logs (they reach `docker logs` immediately), no pip cache.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1. Dependencies first. This layer is rebuilt only when requirements.txt changes,
#    so editing the code does not reinstall numpy and pandas.
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Code and model last: they change most often. Owned by root, so the app cannot modify them.

# 3. Run as an unprivileged user.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app
USER app

# Configuration through the environment (w1d4). No secrets here: anything in ENV is readable
# by everyone who can pull the image (`docker image inspect`).
ENV PYTHONPATH=/app/src \
    FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0

EXPOSE 8000

# python:3.12-slim has no curl; use the standard library. /readyz is 200 only once the model is loaded.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2).status == 200 else 1)"]

# Exec form: uvicorn is PID 1 and receives SIGTERM from `docker stop` directly.
# 0.0.0.0 INSIDE the container; which host interface it is reachable on is decided by `docker run -p`.
CMD ["uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
