# Assessment answers - w6d1 Docker I

## Reasoning questions

**1. A changing build argument near the top.** The Dockerfile reference ("ARG: impact on build
caching") says that every `RUN` after an `ARG` uses the variable implicitly as an environment variable,
so a changed value is a cache miss for each later `RUN`. Measured on this lab with `ARG BUILD_DATE` and
`LABEL build-date=$BUILD_DATE` right after `FROM`, two builds with different dates: `COPY
requirements.txt` stayed `CACHED`, but `RUN pip install` ran again (about 13 s), and so did everything
after it. The `LABEL` itself is image metadata; the reinstall comes from the `ARG` being in scope of the
`RUN`. Fix: declare volatile build arguments (dates, commit hashes) and their labels at the end of the
Dockerfile, after the expensive steps (w6d2 declares `ARG REVISION` in the final stage, after the
dependency install happened in the builder stage). *Common wrong answers:* "labels are metadata, so
nothing changes" (the `RUN` still misses), and "every layer after the LABEL is rebuilt" (the `COPY` of
requirements.txt was cached; only `RUN` instructions see the argument).

**2. Exec form and still 10 s / 137.** PID 1 is now the program itself, and the kernel does not apply
the default action of SIGTERM to a namespace's PID 1: if the program installs no handler, it ignores
SIGTERM (the worked example measures exactly this: 10.24 s with the handler switched off). Fixes:
install a SIGTERM handler that shuts the server down (uvicorn has one; for your own scripts,
`signal.signal(signal.SIGTERM, ...)`), or run with `docker run --init` (or a `tini` entrypoint), which
makes a tiny init PID 1 that forwards signals to the program. Another consistent cause: the handler
exists but shutdown takes longer than 10 s (long requests); then raise `--stop-timeout` or shorten
shutdown. *Common wrong answer:* "use exec form", which is already the case.

**3. Healthy but unreachable.** The server listens on `127.0.0.1` inside the container. The healthcheck
runs *inside* the container, where that address works, so it reports healthy; traffic from the host
arrives on the container's `eth0` interface, where nothing listens, so the connection is reset. Fix:
`--host 0.0.0.0` in the command. *Common wrong answer:* the host firewall; a firewall would give a
timeout or "connection refused", and would not explain the healthy status.

**4. `RUN rm -rf /app/data` at the end.** No. The data is in the layer created by `COPY . .`; the
`rm` adds a new layer that hides the files but the earlier layer is still part of the image and is
pushed and pulled. Fix: keep the data out of the context (`.dockerignore`) and copy only what is
needed (`COPY src/`, `COPY models/`). If something must be created and removed during the build, do
both in the same `RUN`, or build it in another stage (w6d2).

**5. `__pycache__` and `*.pyc` in `.dockerignore`.** Both are anchored at the context root, so
`src/flowguard/__pycache__/*.pyc` and `scripts/__pycache__/*.pyc` still reach the context (as do any
`.pyc` below the root). The reference Dockerfile copies `src/`, so the `src` caches would be copied
into the image: harmless for correctness here, but they are stale bytecode built on your machine,
they make the layer change when nothing in the source changed (so the cache is invalidated more often),
and they are exactly the kind of local residue the image should not contain. Use `**/__pycache__`.

**6. User created after the COPYs.** The copied files stay owned by root and readable by everyone, so
the server (running as `app`) can read but not modify its code and model. A compromised or buggy
process cannot rewrite them. If the files were owned by `app` (`COPY --chown=app` or a `chown -R`),
the server could modify its own code, which defeats part of the point of not running as root. Order
also matters for the cache: `useradd` after the COPYs re-runs on every code change, but it takes 0.1 s.

## Explain a design choice: model baked in, location from the environment (model answer)

Baking the 1 kB bundle into the image makes the image tag a complete description of behaviour: the
same tag always means the same code *and* the same model, which makes deployments reproducible and
rollback trivial (run the previous tag). The cost of baking, a rebuild to change the model, is small
here because the model is tiny and changes as rarely as the code.

Reading the location from `FLOWGUARD_MODEL_DIR` keeps the code independent of the image layout and
lets operators point the same image at a different bundle without a rebuild, for example a candidate
model mounted read-only for a comparison (w6d2 uses this to show a smoke test failing). Hard-coding
the path couples the code to one directory structure and makes tests outside the container awkward.

Mounting only (a) makes the image incomplete: its behaviour depends on what is mounted, so "which
model served this request?" must be logged and checked separately, and the container needs storage
or credentials at start-up. I would switch to (a) when models are large (hundreds of MB to GB), change
much more often than code (daily retraining), or when one image must serve many models; then the
model version must be part of every response and log line, which the API already does.

*Rubric notes.* Strong answers mention both reproducibility/rollback and flexibility, and give a
concrete switching condition. Weak answers argue only "simpler".

## Interview rep: "the container exits immediately" - what a strong answer contains

1. `docker ps -a` (not `docker ps`): the container exists with status `Exited (1)`; `--rm` would have
   removed it, so run without `--rm` while debugging.
2. `docker logs <id>`: the traceback. In this lab the common ones are `ModuleNotFoundError: No module
   named 'flowguard'` (exit 1; PYTHONPATH or install missing) and an import error from a missing
   dependency.
3. `docker inspect --format '{{.State.ExitCode}} {{.State.Error}}' <id>`: 1 = the program failed;
   126/127 = the command is not executable / not found (typo in `CMD`, exec form with a missing
   binary); 137 = killed (memory limit or `docker kill`).
4. Reproduce interactively: `docker run --rm -it --entrypoint sh <image>`, then run the CMD by hand,
   check `echo $PYTHONPATH`, `ls /app`, `python -c "import flowguard"`.
5. Only after it runs: "connection refused" is a separate question (published port, `--host 0.0.0.0`).
6. Before leaving it running at a conference: `-p 127.0.0.1:8000:8000` instead of `-p 8000:8000`
   (otherwise it listens on every interface of the laptop, reachable from the conference Wi-Fi, and
   Docker's rules bypass ufw); `--rm` and a `--name`; never pass credentials on the command line.

| Criterion | Strong | Weak |
|---|---|---|
| Order | starts with `ps -a` and logs before changing anything | rebuilds and retries |
| Exit codes | interprets 1 / 126-127 / 137 | does not use them |
| Interactive reproduction | `--entrypoint sh`, runs the command by hand | none |
| Separates "won't start" from "can't reach" | yes | conflates them |
| Network exposure | loopback publishing, names the Wi-Fi/ufw risk | none |
