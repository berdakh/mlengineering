# Minimal image for the flowguard service (week 6). Lessons w6d1-w6d2 explain every line and
# improve it (multi-stage build, digest-pinned base, smaller image); this one is deliberately plain.
FROM python:3.12-slim

# Run as an unprivileged user, never as root.
RUN useradd --create-home --uid 10001 app
WORKDIR /srv

# Dependencies first: this layer is cached until requirements.lock changes.
# PIP_INSTALL_OPTS lets a build behind a TLS-intercepting proxy install from a local wheelhouse:
#   --build-arg PIP_INSTALL_OPTS="--no-index --find-links=/srv/wheels"
ARG PIP_INSTALL_OPTS=""
COPY requirements.lock ./
COPY wheels/ ./wheels/
RUN pip install --no-cache-dir $PIP_INSTALL_OPTS -r requirements.lock && rm -rf wheels

# The application and its model bundle (the model is part of the release: one image = one model).
# (Put on the import path rather than pip-installed, so the build needs no build backend from PyPI.)
COPY src/ ./src/
COPY models/ /models/

ENV PYTHONPATH=/srv/src \
    FLOWGUARD_MODEL_DIR=/models/flowguard-z/1.0.0 \
    FLOWGUARD_PORT=8000 \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)" || exit 1
CMD ["python", "-m", "flowguard.serve"]
