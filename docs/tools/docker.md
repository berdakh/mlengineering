---
title: "Docker"
parent: Tool guides
nav_order: 13
---

# Docker
{: .no_toc }

Docker packs an application together with everything it needs to run (an operating-system layer, Python, the
libraries, your code and the start command) into an **image**, and runs that image as a **container** on any
machine with Docker. This guide is the reference for [notebook 38](../notebooks/38_docker_from_zero.html) and
[the Week 10 lab](../notebooks/40_lab_container_and_ci.html). The outputs quoted below were produced with
Docker 29.10 on Linux while writing the course; yours will differ in IDs, times and sizes.

1. TOC
{:toc}

## What it is, and why teams use it

A model service needs a particular Python, particular versions of FastAPI and scikit-learn, a model file and a
command to start it. Written instructions ("install Python 3.12, then...") break in many small ways on every new
machine. A Docker image is the finished environment, built once from a recipe (the **Dockerfile**), stored in a
**registry**, and run unchanged on a laptop, a CI runner or a cloud service. That is why almost every model you
deploy will ship as a container image.

| Word | Meaning |
|---|---|
| **image** | a read-only template: file system layers + metadata (start command, user, ports) |
| **container** | a running instance of an image: an isolated process with its own file view and network address |
| **Dockerfile** | the recipe an image is built from |
| **layer** | the file changes made by one Dockerfile step; layers are cached and shared |
| **registry** | a store of images: Docker Hub, GitHub Container Registry (`ghcr.io`), AWS ECR |
| **tag** | a label on an image (`3.12-slim`, `1.4.2`); `latest` is only the default tag |
| **digest** | `sha256:...`, the exact content of an image; it never changes |

Containers share the host's operating-system kernel, which makes them start in about a second and much smaller
than virtual machines; the trade-off is weaker isolation. A container is a packaging and deployment tool, not a
security sandbox.

## Installing it

- **Windows and macOS:** Docker Desktop from docker.com. On Windows it uses WSL 2 (the Windows Subsystem for
  Linux); accept when the installer offers to enable it. Docker Desktop must be running (whale icon) for commands
  to work. Check its licence terms if you use it at a large company.
- **Linux:** Docker Engine (docs.docker.com/engine/install), then `sudo usermod -aG docker $USER` and log out and
  back in, so you do not need `sudo` for every command.
- **Check:** `docker version` shows a Client and a Server section, and `docker run --rm hello-world` prints
  *Hello from Docker!*

Google Colab cannot run Docker. The course grades Dockerfiles as text there and asks you to build and run images
on your own computer.

## A Dockerfile for a Python service

```dockerfile
# 1. Start from a small, pinned Python image
FROM python:3.12-slim

# 2. Work inside /app in the image
WORKDIR /app

# 3. Dependencies first: this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Then the code, which changes more often
COPY app/ app/

# 5. Do not run as root
RUN useradd --create-home appuser
USER appuser

# 6. Document the port, check health, say how to start
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Instruction | Runs when | What it does |
|---|---|---|
| `FROM image:tag` | build | the base image; every Dockerfile starts here |
| `WORKDIR /path` | build | creates the folder and makes it current for what follows |
| `COPY src dest` | build | copies files from the build context into the image |
| `RUN command` | build | runs a shell command and keeps the resulting files as a layer |
| `ENV KEY=value` | build and run | sets an environment variable (visible to anyone with the image) |
| `ARG NAME` | build only | a build-time parameter: `docker build --build-arg NAME=value` |
| `USER name` | build and run | the user for later steps and for the container |
| `EXPOSE 8000` | documentation | records the port the app listens on; it publishes nothing |
| `HEALTHCHECK CMD ...` | run | a command Docker runs periodically inside the container; failure marks it *unhealthy* |
| `CMD [...]` | run | the default command when a container starts; the last `CMD` wins |
| `ENTRYPOINT [...]` | run | a fixed command; `CMD` then supplies its default arguments |

Write `CMD` in **exec form**, a JSON list with double quotes. The shell form, `CMD uvicorn app.main:app`, runs
your program under `/bin/sh -c`, which does not pass on the stop signal, so `docker stop` waits ten seconds and
then kills it. Measured on the course's scorer image: `docker stop` took 10.1 s with the shell form and 0.3 s with
the exec form.

## Layers and the build cache

Each instruction makes a layer. On a rebuild Docker reuses a cached layer when the instruction and its inputs are
unchanged (for `COPY`, the content of the copied files). The first step that changes breaks the cache, and every
later step runs again. Therefore:

- copy `requirements.txt` alone and install **before** copying the code: then a code change re-runs only the
  cheap `COPY`. Measured on the course's small service after editing one line of code: 1.1 s with this order,
  7.0 s with `COPY . .` before `pip install`;
- put things that change rarely near the top, things that change often near the bottom;
- combine related shell commands in one `RUN` with `&&`, and clean up in the same `RUN` (a file deleted in a
  later layer still takes space in the earlier one).

## Building and running

```bash
docker build -t scorer:0.1 .                      # build from ./Dockerfile; tag it scorer:0.1
docker image ls                                   # list images and sizes
docker history scorer:0.1                         # layers and their sizes
docker run --rm -p 8080:8000 scorer:0.1           # run in the foreground; Ctrl+C stops it
docker run -d --rm --name scorer -p 8080:8000 scorer:0.1   # run in the background
docker ps                                         # running containers (docker ps -a: stopped too)
docker logs -f scorer                             # follow the output (Ctrl+C stops following)
docker exec -it scorer bash                       # a shell inside (slim images: use sh if bash is missing)
docker stop scorer                                # stop (with --rm it is also removed)
```

The `.` at the end of `docker build` is the **build context**: the folder whose files Docker may `COPY`. It is
sent to Docker in full, minus what `.dockerignore` excludes.

### Ports

`-p HOST:CONTAINER` forwards a port of your computer to a port inside the container. With `-p 8080:8000` you
visit `http://localhost:8080`, and the server inside must listen on 8000 **on all interfaces**, `0.0.0.0`. A
server listening on `127.0.0.1` inside a container is unreachable from outside it: when we tried, `curl` failed
with `Recv failure: Connection reset by peer`, although the log said the server was running.

### Settings and secrets: environment variables

```bash
docker run --rm -e LOG_LEVEL=debug -e MODEL_PATH=/models/v2.joblib scorer:0.1
docker run --rm --env-file .env scorer:0.1        # many variables from a file (keep .env out of Git and images)
```

Configuration and secrets are given at **run** time, so the same image runs in test and production with
different settings, and secrets never sit inside the image.

### Data: volumes and bind mounts

A container's own files disappear when the container is removed. To keep or share data, mount storage:

```bash
docker run --rm -v "$(pwd)/data:/app/data" scorer:0.1        # bind mount: a folder of your computer
docker volume create preds
docker run --rm -v preds:/app/out scorer:0.1                 # named volume managed by Docker
```

On Windows PowerShell use `${PWD}` instead of `$(pwd)`.

## Small and safe images

- **Slim bases.** On our machine `python:3.12` used 1.62 GB of disk and `python:3.12-slim` 179 MB. The course's
  scorer service image was 215 MB; the lab's API with scikit-learn 570 MB.
- **Pin the base**: a tag that names a version (`python:3.12-slim`) or, stricter, a digest. Never `latest`.
- **`pip install --no-cache-dir`**, so pip's download cache does not stay in the layer.
- **`.dockerignore`** keeps the build context small and private:

  ```
  .git
  .venv
  **/__pycache__
  .env
  notebooks/
  tests/
  ```

  Unlike `.gitignore`, every pattern is matched from the root of the context: `__pycache__` excludes only a
  top-level folder of that name; `**/__pycache__` excludes it at any depth.
- **A non-root `USER`.** `docker exec scorer whoami` should print your user, not `root`.
- **No secrets in the image.** Anything in a layer or an `ENV` can be read by anyone who can pull the image
  (`docker history`, `docker inspect`, or simply running it).
- **A `HEALTHCHECK`.** `docker ps` then shows `(healthy)` or `(unhealthy)`, and orchestrators can restart a
  container that stops answering.

## Registries: sharing images

```bash
docker tag scorer:0.1 ghcr.io/YOUR-USER/scorer:0.1
docker login ghcr.io                     # uses a GitHub token; never type tokens into files you commit
docker push ghcr.io/YOUR-USER/scorer:0.1
docker pull ghcr.io/YOUR-USER/scorer:0.1
```

Pushing to a public registry publishes the image to the world; check what is inside first. Images built on an
Apple-silicon Mac are ARM images; most cloud servers are x86. `docker build --platform linux/amd64 ...` builds
for x86, and building in CI on an x86 runner avoids the question.

## Common errors and how to read them

| You see | It means | Fix |
|---|---|---|
| `Cannot connect to the Docker daemon ... Is the docker daemon running?` | the Docker engine is not running | start Docker Desktop; on Linux `sudo systemctl start docker` |
| `permission denied while trying to connect to the Docker daemon socket` | Linux user not in the `docker` group | `sudo usermod -aG docker $USER`, log out and in |
| `failed to solve: ... "/requirements.txt": not found` | the file is not in the build context, or excluded by `.dockerignore` | run `docker build` in the right folder; check `.dockerignore` |
| `ERROR: Could not find a version that satisfies the requirement x==1.2.3` | that version does not exist for the image's Python or platform | check the version on pypi.org; match the base image's Python |
| `Bind for 0.0.0.0:8080 failed: port is already allocated` | another container or program uses that host port | stop it (`docker ps`), or choose another host port |
| `Conflict. The container name "/scorer" is already in use` | a stopped container kept the name | `docker rm scorer`, or use `--rm` next time |
| Browser: connection refused / reset, container running | no `-p`, wrong port, or the server listens on 127.0.0.1 | `docker ps` shows the mapping; use `--host 0.0.0.0` |
| `exec format error` | the image was built for another CPU architecture | rebuild with `--platform linux/amd64` (or arm64) |
| Container exits immediately | the start command crashed | `docker logs NAME` (or run without `-d` to see the error) |
| `no space left on device` | old images and build cache | `docker system df`, then `docker image prune` / `docker builder prune` |

## Cheat sheet

```bash
# build
docker build -t NAME:TAG .                 # --no-cache to ignore the cache, -f FILE for another Dockerfile
# run
docker run --rm -p HOST:CONT -e K=V -v HOSTDIR:CONTDIR NAME:TAG
docker run -d --name N ...                 # background, named
docker run --rm -it NAME:TAG sh            # a throw-away shell in the image
# inspect
docker ps | docker logs -f N | docker exec -it N sh | docker inspect N
docker image ls | docker history NAME:TAG | docker system df
# stop and clean
docker stop N | docker rm N | docker image rm NAME:TAG | docker system prune
# share
docker tag NAME:TAG REGISTRY/USER/NAME:TAG && docker push REGISTRY/USER/NAME:TAG
```

Dockerfile order to remember: **FROM → WORKDIR → COPY requirements → RUN pip install → COPY code → USER →
EXPOSE → HEALTHCHECK → CMD**.

## Where next

- Official: [Docker get started](https://docs.docker.com/get-started/),
  [Dockerfile reference](https://docs.docker.com/reference/dockerfile/),
  [Building best practices](https://docs.docker.com/build/building/best-practices/), and
  [.dockerignore](https://docs.docker.com/build/concepts/context/#dockerignore-files).
- FastAPI's guide to [FastAPI in containers](https://fastapi.tiangolo.com/deployment/docker/).
- In this course: [notebook 38](../notebooks/38_docker_from_zero.html), the
  [lab](../notebooks/40_lab_container_and_ci.html), [GitHub Actions](github-actions.html) to build images in CI,
  and [cloud basics](cloud-aws.html) for running them in the cloud.
