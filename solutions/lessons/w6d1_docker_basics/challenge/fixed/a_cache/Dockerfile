# Fixed Dockerfile A - REFERENCE SOLUTION (w6d1 challenge).
# Fix: copy only the dependency file before `pip install`; copy code and model after it.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY models/ ./models/
RUN useradd --create-home --uid 10001 app
USER app
ENV PYTHONPATH=/app/src FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0
EXPOSE 8000
HEALTHCHECK CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
