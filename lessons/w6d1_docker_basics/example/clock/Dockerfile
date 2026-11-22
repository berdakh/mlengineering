# syntax=docker/dockerfile:1
# The clock service, containerised properly (w6d1 worked example).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# No dependencies to install, so there is no dependency layer; with requirements.txt it would go here.
COPY app.py .
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin clock
USER clock
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"]
CMD ["python", "app.py"]
