# Hint 3 - partial implementation (w6d2)

The builder stage:

```dockerfile
ARG PYTHON_BASE=python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

FROM ${PYTHON_BASE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv --without-pip /opt/venv
COPY requirements.lock /tmp/requirements.lock
RUN pip --python /opt/venv/bin/python install --require-hashes -r /tmp/requirements.lock
```

The readiness loop of the smoke test:

```python
def wait_until_ready(client, timeout, interval=0.5):
    deadline = time.monotonic() + timeout
    problem = "no attempt made"
    while True:
        try:
            response = client.get("/readyz")
            if response.status_code == 200:
                return None
            problem = f"/readyz answered {response.status_code}"
        except httpx.HTTPError as exc:
            problem = f"{type(exc).__name__}: {exc}"
        if time.monotonic() >= deadline:
            return problem
        time.sleep(interval)
```

What is left: the runtime stage, the labels, `compare` (mind `None` scores during warm-up) and `main`.

**Challenge.** The hash of the validated wheel:

```bash
python -m pip hash lessons/w6d2_docker_reproducibility/challenge/wheelhouse/zscorelib-1.0.0-py3-none-any.whl
```

A lock line is `zscorelib==<version> \` followed by an indented `--hash=sha256:<hex>` line.
