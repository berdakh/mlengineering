# Hint 2 - approach (w6d1)

**Lab, in order.**
1. `FROM python:3.12-slim`, the three `ENV` lines, `WORKDIR /app`.
2. `COPY requirements.txt .` then `RUN pip install --no-cache-dir -r requirements.txt`.
3. `COPY src/ ./src/` and `COPY models/ ./models/` (a directory source copies its *contents* into the
   destination, so `COPY src/ ./src/` gives `/app/src/flowguard/...`).
4. `RUN useradd ...` then `USER <name>`.
5. `ENV PYTHONPATH=/app/src FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0`.
6. `EXPOSE 8000`, `HEALTHCHECK ... CMD [...python urllib...]`, `CMD [...uvicorn...]`.
7. `.dockerignore`: start from `*`, then re-include with `!`.
8. `run_container.sh`: one `docker build -t`, one `docker run --rm --name ... -p 127.0.0.1:8000:8000`.

Run `python wb.py check w6d1` after each step; the failure messages say what is missing.

**Challenge.** A: move one line and add two. B: two changes, one of them in `CMD`. C: write the
`.dockerignore`, run `context_report.py` with it, and repeat until the kept files are only what the
image needs; check that `experiments/*/sweep_*/runs/` and `src/flowguard/__pycache__` are gone.
