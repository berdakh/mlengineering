# Diagnosis of the three broken builds - REFERENCE ANSWER (w6d1 challenge)

## A - slow rebuilds

Symptom: every code edit costs a full dependency install. Mechanism: Docker caches each layer and
reuses it only while the instruction and its inputs are unchanged; for COPY the inputs are the
checksums of the copied files. `COPY . .` sits before `RUN pip install`, so editing one line of
`src/` changes the COPY layer, and every later layer, including the 171 MB install, is rebuilt.
Fix: `COPY requirements.txt .` then `RUN pip install`, then `COPY src/` and `COPY models/`. The
install layer now depends only on requirements.txt. Verified: the static check passes; in the
lesson's measurement the same edit rebuilt in 1.7-2.0 s instead of 20.2-21.4 s.

## B - slow, ungraceful stops and root

Symptom: `docker stop` takes ~10 s and the container exits with 137, without uvicorn's shutdown
log. Mechanism: a shell-form CMD runs as `/bin/sh -c "..."`, so the shell is PID 1. `docker stop`
sends SIGTERM to PID 1 only; the shell neither handles it (PID 1 has no default signal actions) nor
forwards it, so after the 10 s grace period Docker sends SIGKILL. With `&&` the shell cannot even
replace itself with uvicorn. The process also ran as root because no USER was set.
Fix: exec-form CMD starting uvicorn directly, plus `useradd` and `USER app`. Verified: in the
lesson's measurement exec form stopped in 0.5-0.6 s with exit code 0 and "Finished server process".

## C - huge context, huge image, leaked .env

Symptom: minutes of "transferring context", a 1 GB image, and `.env` inside it. Mechanism: without
a .dockerignore, `docker build .` sends the whole directory (1,050 MB here: .venv, data, nested
experiment checkpoints, .git) to the builder, and `COPY . .` then writes all of it, secrets
included, into an image layer. Deleting a file in a later layer does not remove it from the
earlier one. Fix: an allow-list .dockerignore (exclude `*`, re-include requirements.txt, src,
models; exclude `**/__pycache__`). Verified with context_report.py: 12 of 398 files, 0.04 MB
are sent; `.env`, `.venv`, `data`, `.git` and every `runs/` directory are out.
