# Broken build C (w6d1 challenge). The Dockerfile itself is reasonable; the problem is what
# `docker build .` sends to the builder. The project directory it is run from is described, file by
# file, in context_listing.tsv (about 1.1 GB). There is no .dockerignore. The complaints:
# "the build spends a minute on 'transferring context'", "the image is 1 GB" and
# "someone found our .env in the image".
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 app
USER app
ENV PYTHONPATH=/app/src FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0
EXPOSE 8000
CMD ["uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
