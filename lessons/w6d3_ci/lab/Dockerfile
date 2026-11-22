# Minimal single-stage image for the flowguard API (w6d1 builds this up properly: multi-stage,
# lockfile, pinned base digest). Build and run:
#   docker build -t flowguard:dev .
#   docker run --rm -p 127.0.0.1:8000:8000 flowguard:dev
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY models ./models

RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
CMD ["uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
