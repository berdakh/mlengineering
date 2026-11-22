# Fixed Dockerfile B - REFERENCE SOLUTION (w6d1 challenge).
# Fixes: (1) exec-form CMD, so uvicorn is PID 1 and receives SIGTERM from `docker stop`;
#        (2) an unprivileged user. The start-up message moved into the application log
#        (uvicorn prints its own start-up lines); if you need a wrapper script, end it with
#        `exec uvicorn ...` so the shell is replaced by the server.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
COPY models/ ./models/
RUN useradd --create-home --uid 10001 app
USER app
ENV PYTHONPATH=/app/src FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0
EXPOSE 8000
HEALTHCHECK CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
