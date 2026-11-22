# Assessment - w6d1 Docker I

Answer before opening `solutions/lessons/w6d1_docker_basics/assessment_answers.md`. 20-25 minutes.

## Reasoning questions

1. Your Dockerfile installs dependencies, then copies code. A colleague adds `ARG BUILD_DATE` and
   `LABEL build-date=$BUILD_DATE` right after `FROM` and passes the current time on every build. What
   happens to rebuild times, and why? Where should those two lines go?
2. `docker stop` on your container takes 10 s and the exit code is 137, but `CMD` is already in exec
   form. Give a cause consistent with this and two ways to fix it.
3. The container is `healthy` according to `docker ps`, but `curl http://127.0.0.1:8000/readyz` from
   the host fails with "connection reset by peer". What is the most likely cause, and why does the
   healthcheck not notice?
4. A teammate adds `RUN rm -rf /app/data` at the end of the Dockerfile to "remove the data that `COPY . .`
   brought in". Does the image get smaller? What should they do instead?
5. Your `.dockerignore` contains `__pycache__` and `*.pyc`. Which `.pyc` files still reach the build
   context in this lab, and does it matter for the image the reference Dockerfile builds?
6. Why does the reference Dockerfile create the user *after* the `COPY` instructions rather than
   before them, and what would change if the files were owned by that user?

## Explain a design choice (150-250 words)

The image bakes in the 1 kB model bundle and reads its location from `FLOWGUARD_MODEL_DIR`. Argue for
this choice over (a) mounting the model at run time only and (b) hard-coding the path in the code.
Then describe the situation in which you would switch to (a).

## Rubric for the open-ended answers

| Criterion | Strong | Adequate | Weak |
|---|---|---|---|
| Cache mechanics (Q1) | an ARG in scope is part of every later RUN's cache key, so pip reinstalls; move ARG + LABEL to the end | "breaks the cache" without which instructions | thinks labels or args are free |
| Signals (Q2) | PID 1 has no default SIGTERM action; program installs no handler; fix: handler, or `--init`/tini | names one cause | "use exec form" only |
| Networking (Q3) | server bound to container loopback; healthcheck runs inside the container | right cause, no reason for healthy | firewall guesses |
| Layers (Q4) | earlier layer still contains the data; use .dockerignore or targeted COPY | "no" without mechanism | "yes" |
| Ignore semantics (Q5) | root-anchored; nested caches reach the context; reference COPYs only src/models, and src caches would be copied | partial | treats like .gitignore |
| Least privilege (Q6) | root-owned code is read-only for the server; compromise cannot rewrite code or model | "security" without mechanism | no answer |
| Design choice | weighs reproducibility (image = code + model), rollback, image size, flexibility; switches to mounting when models are large or change independently | one side argued | assertion |

## Interview rep (12 minutes, debugging, reduced assistance)

Answer aloud or in writing, timed, without notes:

> "I built the image, `docker run -d -p 8000:8000 myapi` returns an ID, but `docker ps` shows nothing
> and `curl localhost:8000` says connection refused. Walk me through how you debug this, in order,
> naming the exact commands and what each result would tell you. Then: once it runs, what in my
> `docker run` command would you change before I leave it running on my laptop at a conference?"

Self-score with the interview rubric in the answers file *after* answering.
