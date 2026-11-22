# Hint 3 - partial implementation (w6d1)

The middle of the lab Dockerfile (you still need the head and the tail):

```dockerfile
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY models/ ./models/

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app
USER app

ENV PYTHONPATH=/app/src \
    FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0
```

A healthcheck that needs no extra package:

```dockerfile
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2).status == 200 else 1)"]
```

The start of an allow-list `.dockerignore`:

```text
*
!requirements.txt
!src
```

(two more lines are needed: one re-include, one exclusion at any depth).

**Challenge B.** If you want to keep the start-up `echo`, the shell must hand over PID 1:
`CMD ["sh", "-c", "echo starting && exec uvicorn ..."]`. Without `exec` it is still the shell.
