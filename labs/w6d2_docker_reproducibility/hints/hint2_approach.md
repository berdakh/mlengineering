# Hint 2 - approach (w6d2)

**Lab.**
1. `uv pip compile requirements.in --generate-hashes --python-version 3.12 --python-platform linux -o requirements.lock`.
   Run the lockfile checks.
2. Dockerfile: `ARG PYTHON_BASE=python:3.12-slim@sha256:...` at the very top; `FROM ${PYTHON_BASE} AS builder`;
   venv without pip; `COPY requirements.lock`; install with `pip --python /opt/venv/bin/python install --require-hashes -r ...`.
3. `FROM ${PYTHON_BASE} AS runtime`; `COPY --from=builder /opt/venv /opt/venv`; `ENV PATH=/opt/venv/bin:$PATH`;
   then the w6d1 runtime instructions; `ARG VERSION`, `ARG REVISION` and the two OCI labels.
4. smoke_test.py: a `while True` loop with a monotonic deadline around `client.get("/readyz")`,
   catching `httpx.HTTPError`; then one POST; then a comparison loop over the 300 results.

**Challenge.**
1. Run `./build.sh` and read the `installed:` line. Open both wheels' `zscorelib/__init__.py`
   (`python -m zipfile -l` lists a wheel; `unzip -p wheel zscorelib/__init__.py` prints the file) or
   the sources in `pkgsrc/`.
2. Decide which version is *correct* for this service (which one produced the recorded scores?).
3. Write `service/requirements.lock` with that version and its hash (`python -m pip hash <wheel>`).
4. Change `build.sh` to install the lock with `--require-hashes`.
