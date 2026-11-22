# w6d1 - Docker I: images, layers and a correct Dockerfile

**Status: Execution verified** (see the verification record at the end).

| | |
|---|---|
| **Primary objective** | Explain what an image and a container are, and write a Dockerfile for the flowguard API that runs as an unprivileged user, rebuilds fast after a code edit, sends only what it needs to the builder, stops cleanly, and is reachable only from your own machine. |
| **Deliverable** | `lab/Dockerfile`, `lab/.dockerignore` and `lab/run_container.sh`; a running container that returns the expected scores for the smoke request. |
| **Completion criteria** | `python wb.py check w6d1` passes (static checks, no Docker needed); if you have Docker: the container answers `/readyz`, returns the 300 expected scores, and `docker stop` takes under a second. You can explain, without notes, why a shell-form `CMD` makes every stop take 10 s. |
| **Handbook** | [H12.1 Images, layers and Dockerfiles](../../handbook/ch12_docker_reproducible_environments/h12_1_images_layers_dockerfiles.md) |

---

## 1. Purpose

**What you will learn.** How a Dockerfile becomes an image and an image becomes a running container;
how the build cache decides what is rebuilt; what the build context is and how `.dockerignore`
filters it; why the form of `CMD` decides whether your server ever sees `docker stop`; how ports are
published and why `0.0.0.0` inside the container is right while `-p 8000:8000` on your laptop is not;
where the model and the configuration should live; and how a healthcheck reports "ready".

**Why an applied ML engineer needs it.** "It runs on my machine" is the default failure of research
code. A container image is the unit that every later step of this course ships: CI builds it (w6d3),
the cloud runs it (w6d5), monitoring watches it (Week 7). Interviewers ask you to write or review a
Dockerfile, and reviewers in industry will reject an image that runs as root, rebuilds all
dependencies on every commit, or bakes in a `.env` file. Each of those mistakes is measured below.

**Prerequisites.**
* [w5d6](../w5d6_project_milestone_2/README.md): the API and the model bundle. This lab ships a
  snapshot of the Week 5 service (`flowguard` 0.6.0) so it runs even if your milestone is unfinished.
* [w1d4](../w1d4_config_logging/README.md): configuration through the environment; secrets never in files.
* For the live parts: Docker Engine on your laptop (section 4.0 has the Pop!_OS notes). Without
  Docker you can still do the whole guided lab: the checks are static.

**Time budget (2 h essential + optional extension up to 1 h).**

| Activity | Minutes |
|---|---|
| Read sections 2 and 3 | 30 |
| Run the worked example (needs Docker; otherwise read its recorded output) | 10 |
| Guided lab: Dockerfile, .dockerignore, run script, live run | 60 |
| Start the independent challenge (three broken builds) | 10 |
| Assessment questions and reflection | 10 |
| *Optional extension*: finish the challenge; run the live check (`WB_DOCKER=1`) and measure your own stop and rebuild times | up to 60 |

---

## 2. Conceptual explanation

### 2.1 Intuition: an image is a frozen filesystem plus a default command

An **image** is a read-only, layered filesystem (Debian files, Python, your packages, your code, your
model) plus metadata: which command to run, as which user, with which environment variables and
which port. A **container** is a running process started from that image, with its own view of the
filesystem, its own process tree and its own network interface, plus a thin writable layer that is
thrown away with the container.

```mermaid
flowchart LR
    subgraph host["your laptop"]
        ctx["build context<br/>(lab/ minus .dockerignore)"]
        df["Dockerfile"]
    end
    ctx --> builder
    df --> builder["builder (BuildKit)<br/>runs each instruction"]
    builder --> img["image flowguard:0.6.0<br/>layers + metadata"]
    img -->|"docker run"| c1["container 1<br/>PID 1 = uvicorn"]
    img -->|"docker run"| c2["container 2"]
    c1 -->|"docker stop: SIGTERM, then SIGKILL after 10 s"| gone["exited"]
```

The image is built once and run many times, identically: on your laptop, in CI, in the cloud. That is
the whole point, and it is also why everything that *differs* between those places (the model
version to load, credentials, the port) must come in from outside at run time.

### 2.2 Precise terms

| Term | Meaning |
|---|---|
| **Container** | A normal Linux process, isolated by kernel **namespaces** (its own process IDs, mount table, network interfaces, hostname, users) and limited by **cgroups** (CPU, memory). It is not a virtual machine: there is no second kernel. |
| **Layer** | The filesystem change made by one Dockerfile instruction (`RUN`, `COPY`, `ADD`). Layers are stacked by a union filesystem; a file "deleted" in a later layer still exists in the earlier one. |
| **Build context** | The directory (`docker build <dir>`) whose files may be copied into the image, minus what `.dockerignore` excludes. Only it is visible to `COPY`. |
| **Build cache** | A layer is reused if its instruction and its inputs are unchanged. For `COPY` the inputs are the checksums of the copied files; for `RUN`, the command text and every earlier layer. |
| **Tag / digest** | `python:3.12-slim` is a movable name. `python@sha256:5e2b...` is the content address of one exact image. w6d2 pins by digest. |
| **Exec form / shell form** | `CMD ["uvicorn", "..."]` runs the program directly. `CMD uvicorn ...` runs `/bin/sh -c "uvicorn ..."`. |
| **PID 1** | The first process in the container's process namespace. It receives `docker stop`'s SIGTERM, and the kernel does not apply default signal actions to it. |
| **Publish (`-p`)** | Forward a host address and port to a container port: `-p 127.0.0.1:8000:8000` means "host loopback port 8000 to container port 8000". |
| **Healthcheck** | A command Docker runs inside the container periodically; its exit status becomes the container's `health` (`starting`, `healthy`, `unhealthy`). |

### 2.3 The build cache, and the order of instructions

Each instruction produces a layer, and a layer is valid only as long as every layer below it is.
Change the input of one instruction and that layer *and every layer after it* is rebuilt. So order
instructions from "changes rarely" to "changes often":

```mermaid
flowchart TB
    subgraph good["dependencies first"]
        direction TB
        g1["FROM python:3.12-slim"] --> g2["COPY requirements.txt"] --> g3["RUN pip install (171 MB, ~13 s)"] --> g4["COPY src/ (70 kB)"] --> g5["COPY models/"]
    end
    subgraph bad["COPY . . first"]
        direction TB
        b1["FROM python:3.12-slim"] --> b2["COPY . ."] --> b3["RUN pip install (171 MB, ~13 s)"]
    end
    edit(["edit one line of src/flowguard/api.py"]) -.->|"invalidates"| g4
    edit -.->|"invalidates"| b2
    b2 -.->|"and everything after"| b3
```

If the cost of a layer is *c<sub>i</sub>* and a change hits layer *k*, the rebuild costs
Σ<sub>i ≥ k</sub> *c<sub>i</sub>*. Putting the expensive, stable step (dependency install) before the
cheap, volatile ones (your code) makes *k* land after it for almost every commit. Measured on this
lab (section 3.2): 1.8 s versus 20.9 s per rebuild. In CI, which often starts from a colder cache, the
difference is minutes per commit.

### 2.4 The build context and `.dockerignore`

`docker build .` hands the directory to the builder. Two facts surprise most people:

1. **Patterns are anchored at the context root.** `__pycache__` in `.dockerignore` excludes only
   `./__pycache__`, not `src/flowguard/__pycache__`; that needs `**/__pycache__`. This is the
   opposite of `.gitignore`, and the worked example verifies it against a real build.
2. **BuildKit sends only what the Dockerfile references.** With targeted copies
   (`COPY requirements.txt`, `COPY src/`), a 344 MB pile of local data next to the Dockerfile cost
   72 kB of transfer even without a `.dockerignore`. With `COPY . .` the same directory sent 360 MB
   and every byte ended up in the image. A `.dockerignore` is still necessary: it is the guard for
   the day someone writes `COPY . .`, and it keeps secrets such as `.env` out of the context entirely.

An allow-list is the robust form: exclude `*`, re-include the few paths the image needs. New
directories (next month's `experiments/`) then stay out by default.

### 2.5 Exec form, PID 1 and signals

`docker stop` sends SIGTERM to the container's PID 1, waits 10 seconds by default, then sends SIGKILL.
Two things decide whether your server shuts down cleanly in that window:

* **Who is PID 1.** With the shell form, PID 1 is `/bin/sh -c "..."`. The Debian shell (dash) neither
  forwards SIGTERM to its child nor replaces itself with the child, so uvicorn never hears the
  signal. With the exec form, uvicorn *is* PID 1.
* **Whether PID 1 handles SIGTERM.** The kernel does not apply default signal actions (such as
  "terminate on SIGTERM") to a namespace's PID 1. A program that installs no handler ignores the
  signal there, even though the same program dies on SIGTERM on your laptop. uvicorn installs a
  handler and shuts down gracefully; a plain Python script must install its own (section 3.1 shows
  both cases).

```mermaid
sequenceDiagram
    participant D as docker stop
    participant S as PID 1 = /bin/sh (shell form)
    participant U as uvicorn
    D->>S: SIGTERM
    Note over S: no handler, not forwarded
    Note over U: keeps serving
    D-->>D: wait 10 s
    D->>S: SIGKILL (exit 137)
    Note over U: killed mid-request
```

With exec form the same sequence is: SIGTERM to uvicorn, uvicorn stops accepting connections, finishes
in-flight requests, runs the lifespan shutdown, exits 0. In an orchestrator that restarts or scales
containers all day, the shell form turns every deployment into dropped requests and 10 s delays.

### 2.6 Ports: inside and outside

Inside the container, the server must listen on `0.0.0.0`, all of the *container's* interfaces.
`127.0.0.1` inside the container is the container's own loopback, which the host cannot reach: the
port is published, the connection arrives, and nothing is listening on the interface it arrives on
(measured: `curl: (56) Recv failure: Connection reset by peer`, while the in-container healthcheck
still reported `healthy`).

Which *host* interface is exposed is decided by `docker run -p`. Without a host IP, `-p 8000:8000`
listens on every host interface, so anyone on your Wi-Fi can call your model; Docker's install
documentation also warns that published ports bypass `ufw` firewall rules. On a laptop, publish on
loopback only: `-p 127.0.0.1:8000:8000`.

```mermaid
flowchart LR
    you["curl on your laptop<br/>127.0.0.1:8000"] -->|"-p 127.0.0.1:8000:8000"| nat["docker port forward"]
    lan["another machine<br/>on your Wi-Fi"] -.->|"only if -p 8000:8000"| nat
    nat --> c["container eth0:8000"]
    c --> u["uvicorn --host 0.0.0.0"]
    c -.-x l["uvicorn --host 127.0.0.1<br/>(container loopback only)"]
```

### 2.7 Where the model and the configuration live

| Choice | For | Against |
|---|---|---|
| **Bake the model into the image** (`COPY models/`) | one artifact: image tag = code + model; trivially reproducible; rollback = previous tag | rebuild and re-push to change the model; large models make large images |
| **Mount the model at run time** (`-v /models:/models:ro`, or download at start) | change models without rebuilding; one image serves many models | the image alone no longer determines behaviour; the container needs storage or credentials; "which model was running?" must be logged |

This course bakes the small (1 kB) bundle in, and reads its *location* from `FLOWGUARD_MODEL_DIR`, so
the same image can be pointed at a mounted candidate model without a rebuild (w6d2 does exactly that
to show a smoke test failing). Configuration that differs between environments goes in environment
variables (w1d4). **Secrets never go into the Dockerfile, the context or an `ENV`**: anyone who can
pull the image can read every layer and `docker image inspect` shows every `ENV`.

### 2.8 Connection to what you already know

A container is the deployment-time version of a frozen research environment: the conda environment
and the exact analysis code behind a paper figure. What changes is the bar. A reviewer of a paper
reruns your analysis once; an orchestrator starts, stops and replaces your container hundreds of
times, and expects it to start in seconds, stop on request, report readiness and contain nothing it
does not need. Real-time BCI work is the closest analogue you have: a process that must start and stop
cleanly on command and must not hold the amplifier when killed. SIGTERM handling is that, for servers.

### 2.9 An industry example

A team ships a churn-scoring API in a container built `FROM python:3.11` with `COPY . .` and
`CMD python serve.py`. Three symptoms arrive over a month: CI takes six minutes per commit (every
commit reinstalls dependencies, and the 1 GB base image is pulled on fresh runners); each deployment
drops a few requests (shell-form CMD and no SIGTERM handler: old containers are killed, not drained);
and a security scan finds the developers' `.env` with a database password in layer 3. None of these is
a modelling problem, all three are fixed in the Dockerfile, and each is checked by this lab.

### 2.10 Limitations and common misconceptions

* **"A container is a lightweight VM."** It shares the host kernel. Isolation is weaker than a VM's;
  running as root inside a container is root on the host's kernel, with only namespaces and
  capabilities in between. Hence the unprivileged user.
* **"`RUN rm` makes the image smaller."** A file added in one layer and removed in a later one is
  still shipped in the earlier layer. Do not add it (`.dockerignore`), or add and remove it in the
  same `RUN`, or use a multi-stage build (w6d2).
* **"`EXPOSE` publishes the port."** It documents the port; `docker run -p` publishes it.
* **"Healthy means reachable."** The healthcheck runs inside the container; it says nothing about
  the port mapping or the host firewall.
* **"Exec form is enough for graceful shutdown."** Only if the program handles SIGTERM as PID 1.
  uvicorn does; a bare Python script does not (section 3.1). `docker run --init` adds a tiny init
  process that forwards signals, if you cannot change the program.
* **"Build arguments only affect the instruction that uses them."** Every `RUN` after an `ARG` sees
  it as an environment variable, so a changing value (a build date, a commit hash) is a cache miss for
  every later `RUN`. Measured here: `ARG BUILD_DATE` right after `FROM` made `pip install` run again on
  every build while `COPY requirements.txt` stayed cached. Declare volatile arguments at the end.
* **"The image is reproducible because it has a Dockerfile."** `python:3.12-slim` and an unpinned
  `pip install` resolve differently next month. That is w6d2.

---

## 3. Worked example: a clock service, naive and careful

Everything in this section was run on 2026-11-22 with Docker Engine 29.10.0; the outputs are copied
from those runs. Timings depend on your machine; the ratios are the lesson.

### 3.1 Signals and users: `example/clock/`

`example/clock/app.py` is a 70-line JSON clock server using only the standard library (so it builds in
seconds, with nothing to install). `CLOCK_HANDLE_SIGTERM=0` switches its SIGTERM handler off.
`Dockerfile.naive` is the usual first attempt; `Dockerfile` is careful:

```dockerfile
# Dockerfile.naive                      # Dockerfile (careful)
FROM python:3.12-slim                   FROM python:3.12-slim
WORKDIR /app                            ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY . .                                WORKDIR /app
CMD python app.py                       COPY app.py .
                                        RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin clock
                                        USER clock
                                        EXPOSE 8080
                                        HEALTHCHECK ... CMD ["python", "-c", "import urllib.request; ..."]
                                        CMD ["python", "app.py"]
```

Run it (it builds two images, runs each version, measures `docker stop`, and cleans up its containers):

```bash
bash lessons/w6d1_docker_basics/example/run_example.sh
```

```text
naive (shell form, root)           stop 10.24 s   user root   PID 1: /bin/sh -c python app.py
    GET / -> {"time": "2026-11-22T17:33:48+00:00", "uptime_s": 0.1, "pid": 7}
good (exec form, handler)          stop  0.46 s   user clock  PID 1: python app.py
    GET / -> {"time": "2026-11-22T17:33:59+00:00", "uptime_s": 0.1, "pid": 1}
good image, handler switched off   stop 10.24 s   user clock  PID 1: python app.py
    GET / -> {"time": "2026-11-22T17:34:01+00:00", "uptime_s": 0.1, "pid": 1}
clock:good  178MB
clock:naive  178MB
```

**Interpretation.** The naive image runs the server as PID 7 under a shell, as root, and every stop
takes the full 10 s grace period plus the kill. The careful image runs the server as PID 1, as
`clock`, and stops in under half a second. The third line is the subtle one: same careful image,
same exec form, but with the handler switched off the stop takes 10 s again, because the kernel does
not give PID 1 the default "terminate" action for SIGTERM. Exec form is necessary, not sufficient.
Remove the images afterwards with `docker image rm clock:naive clock:good`.

### 3.2 The same mechanisms on the flowguard API

The reference solution of the lab (`solutions/lessons/w6d1_docker_basics/lab/Dockerfile`) was built
and then varied one property at a time. Raw numbers are in `figures/measurements.json`; the figures
are drawn by `python lessons/w6d1_docker_basics/figures/make_figures.py`.

![Exec form stops in about half a second; both shell forms take just over 10 s](figures/stop_time.svg)

*Figure 1 (measured, 3 runs each).* `docker stop` returns in 0.5 s when uvicorn is PID 1 (exit code 0,
log ends with "Finished server process") and in 10.2-10.4 s with either shell form (exit code 137 =
128 + SIGKILL). A shell wrapper is fine if it ends with `exec uvicorn ...`.

![Copying requirements.txt first makes a code edit rebuild in about 2 s instead of 21 s](figures/rebuild_time.svg)

*Figure 2 (measured, 3 runs).* Rebuild after appending a comment to `src/flowguard/api.py`. With
`COPY . .` before `pip install` every edit reinstalls numpy and pandas.

![The image is 178 MB of base and 171 MB of dependencies; code, model and user are kilobytes](figures/image_layers.svg)

*Figure 3 (`docker history`).* What the 395 MB (on disk; 90 MB compressed) image consists of. Your
own code is 70 kB. Making the image smaller therefore means a smaller base or fewer dependencies, not
cleverer COPYs; w6d2 measures what a multi-stage build does and does not buy.

![Without .dockerignore, COPY . . sends 360 MB and the compressed image grows from 90 MB to 450 MB](figures/dockerignore_effect.svg)

*Figure 4 (measured).* A copy of the lab with 300 MB of `data/raw`, 40 MB of `runs/`, 20 MB of `.git`
and a `.venv` added, built with a `COPY . .` Dockerfile. With the targeted copies of the reference
Dockerfile the same directory sent only 72 kB even without `.dockerignore` (BuildKit transfers only
referenced paths), which is why the guard matters most exactly when someone writes `COPY . .`.

Three failure modes seen while building it, each one a line of the debugging table in section 4.5:

```text
# --host 127.0.0.1 inside the container
$ curl -sS http://127.0.0.1:8768/healthz
curl: (56) Recv failure: Connection reset by peer
$ docker inspect --format '{{.State.Health.Status}}' fgw6lb
healthy

# FLOWGUARD_MODEL_DIR pointing at the models root
$ curl -s http://127.0.0.1:8769/readyz
{"error":{"code":"not_ready","message":"the model is not loaded",...}}
$ docker logs ... | grep "model not loaded"
model not loaded: /app/models: checksums.json missing

# the package not on PYTHONPATH (docker run -e PYTHONPATH= ...)
ModuleNotFoundError: No module named 'flowguard'
exit=1
```

### 3.3 `.dockerignore` is not `.gitignore`

```bash
python lessons/w6d1_docker_basics/example/dockerignore_demo.py --docker   # drop --docker to run offline
```

```text
.dockerignore:
  __pycache__
  *.pyc
  runs
  **/.ipynb_checkpoints
  *.md
  !README.md
  data

file                                   in context?
  README.md                              sent
  __pycache__/b.pyc                      EXCLUDED
  a.pyc                                  EXCLUDED
  data/raw/x.csv                         EXCLUDED
  docs.md                                EXCLUDED
  exp/2026/runs/m.bin                    sent
  notebooks/.ipynb_checkpoints/n.ipynb   EXCLUDED
  runs/r.bin                             EXCLUDED
  src/b.pyc                              sent
  src/notes.md                           sent
  src/pkg/__pycache__/a.cpython-312.pyc  sent
  src/pkg/a.py                           sent

real docker build agrees with the prediction: True
```

Every pattern without `**/` matched only at the root: the nested `__pycache__`, `src/b.pyc`,
`src/notes.md` and `exp/2026/runs/` were all sent. The prediction comes from
`checks/w6d1_dockerlint.py`, a port of Docker's own matcher (moby/patternmatcher); the `--docker` run
builds `COPY . /ctx` into a busybox image and lists what arrived. The lab's checks use the same matcher.

---

## 4. Guided lab

Work in `lessons/w6d1_docker_basics/lab/`. It already contains the Week 5 service snapshot; you write
`Dockerfile`, `.dockerignore` and `run_container.sh` (table in `lab/README.md`).

### 4.0 Docker on Pop!_OS (once; skip if `docker info` works)

Docker's documentation installs Docker Engine on Ubuntu from Docker's own `apt` repository. Pop!_OS is
an Ubuntu derivative, which that page says is "not officially supported (though it may work)"; its
repository snippet uses `UBUNTU_CODENAME`, which Pop!_OS sets, so the Ubuntu instructions are the ones
to follow: <https://docs.docker.com/engine/install/ubuntu/>, then the post-installation page for
running `docker` without `sudo`. Not verified on Pop!_OS by the course author. Read the warning at the
top of that page: ports published by Docker bypass `ufw`. Podman (`sudo apt install podman`) is a
daemonless alternative that reads the same Dockerfiles; the commands here use `docker`.

Check: `docker run --rm hello-world` prints "Hello from Docker!".

### 4.1 Base, environment, working directory

Start `lab/Dockerfile` with an explicitly tagged official Python image and three environment
variables:

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
```

`slim` is Debian with Python and little else (179 MB against 1.62 GB for `python:3.12`). Unbuffered
output makes `print` and log lines appear in `docker logs` immediately.

*Checkpoint:* `python wb.py check w6d1` now passes `test_base_image_has_an_explicit_python_tag`.

### 4.2 Dependencies first, code last

Copy `requirements.txt` alone, install it, then copy `src/` and `models/`. Install the *serving*
requirements only: `requirements-dev.txt` holds scipy, pytest and httpx, which the server never
imports (scipy is only needed by `scripts/build_bundle.py`, a training-side script).

*Checkpoint:* `test_dependencies_are_installed_before_the_code_is_copied` and
`test_build_does_not_bake_in_the_training_tools` pass.

### 4.3 User, configuration, port, healthcheck, command

1. Create a user with a fixed UID (for example `useradd --create-home --uid 10001 --shell /usr/sbin/nologin app`)
   and switch to it with `USER app`. Put this after the COPYs: the code stays owned by root, so the
   server cannot modify its own code or model.
2. `ENV PYTHONPATH=/app/src` (the package is copied, not installed) and
   `ENV FLOWGUARD_MODEL_DIR=/app/models/flowguard-z/1.0.0`.
3. `EXPOSE 8000`.
4. A `HEALTHCHECK` that requests `/readyz`. The slim image has no `curl`; use
   `python -c "import sys, urllib.request; ..."` in exec form.
5. `CMD` in exec form: `uvicorn --factory flowguard.api:create_app_from_env --host 0.0.0.0 --port 8000`.
   `--factory` tells uvicorn to call `create_app_from_env()` to obtain the app; the factory reads
   `FLOWGUARD_MODEL_DIR`.

*Checkpoint:* `test_the_image_layout_finds_the_app_and_the_model` passes. This check follows your
`WORKDIR`, `COPY` and `ENV` exactly as Docker would and then loads the bundle from the directory
`FLOWGUARD_MODEL_DIR` points to; it is the static stand-in for "the container becomes ready".

### 4.4 `.dockerignore` and the run script

1. Create `lab/.dockerignore`. It must keep out `.git`, `.venv`, `data`, `runs`, `.env` and every
   `__pycache__` at any depth, and must keep in what your COPYs need. An allow-list (`*` then `!src`,
   `!models`, `!requirements.txt`, then `**/__pycache__`) is the most robust answer.
2. Complete `lab/run_container.sh`: `docker build -t flowguard:0.6.0 .`, then
   `docker run --rm --name flowguard -p 127.0.0.1:8000:8000 flowguard:0.6.0`.

*Checkpoint:* `python wb.py check w6d1` passes completely (29 checks; one live test is skipped).

### 4.5 Run it (if you have Docker)

```bash
cd lessons/w6d1_docker_basics/lab
./run_container.sh --detach
curl -s http://127.0.0.1:8000/readyz
curl -s -X POST -H 'Content-Type: application/json' --data @smoke/request.json \
     http://127.0.0.1:8000/predict | python -m json.tool | head -20
docker inspect --format '{{.State.Health.Status}}' flowguard      # "healthy" after ~10 s
docker exec flowguard id                                          # uid=10001(app)
time docker stop flowguard                                        # well under a second
docker image ls flowguard; docker history flowguard:0.6.0
```

Then the full live check, which builds, runs, compares all 300 scores with `smoke/expected.json`,
checks the user and the stop time, and cleans up:

```bash
WB_DOCKER=1 python -m pytest lessons/w6d1_docker_basics/checks -q -k live
```

On real SKAB data (after `python project/get_skab.py`):
`python lab/scripts/make_request.py --experiment valve1/13 --out /tmp/req.json`, then POST `/tmp/req.json`.

**Debugging table.**

| Symptom | Likely cause | Look at |
|---|---|---|
| Container exits immediately, exit code 1 | the command fails at start: wrong module path, missing `PYTHONPATH`, typo in the factory name | `docker logs <name>` (the traceback is there) |
| Exit code 137 after `docker stop` | SIGKILL after 10 s: shell-form CMD, or PID 1 without a SIGTERM handler | `docker exec <name> cat /proc/1/cmdline` |
| `curl: (56) Connection reset by peer` or `(52) Empty reply` | the server listens on 127.0.0.1 *inside* the container | the `--host` in CMD |
| `curl: (7) Failed to connect` | not published, wrong host port, or container not running | `docker ps` (PORTS column) |
| `/readyz` 503 forever | `FLOWGUARD_MODEL_DIR` wrong, or the model not copied | `docker logs`, `docker exec <name> ls -R /app/models` |
| Health `unhealthy` but the API works from the host | the healthcheck command itself fails (e.g. `curl` not installed) | `docker inspect --format '{{json .State.Health}}' <name>` |
| `pip install` fails with certificate errors during the build | a TLS-intercepting proxy (corporate networks) | ask for the proxy CA; never disable verification |
| "transferring context" takes long | `COPY . .` and no or weak `.dockerignore` | the size printed by `docker build`; `challenge/context_report.py` |

---

## 5. Independent challenge: three broken builds

[challenge/README.md](challenge/README.md): three Dockerfiles that all build and serve predictions,
each with a complaint from its team (slow rebuilds; slow, ungraceful stops and root; a 1 GB context
with a leaked `.env`). Fix each and write `challenge/DIAGNOSIS.md`: symptom, mechanism, fix,
verification. Build C is described by a 398-file listing of a 1.05 GB project, so you can measure your
`.dockerignore` without the gigabyte: `python lessons/w6d1_docker_basics/challenge/context_report.py ...`.

Acceptance criteria are in the challenge README. Check with `python wb.py check w6d1 --challenge`.

---

## 6. Progressive hints

Open them one at a time, only after a real attempt.

1. [Concept](hints/hint1_concept.md)
2. [Approach](hints/hint2_approach.md)
3. [Partial implementation](hints/hint3_partial.md)

The full reference solution is in `solutions/lessons/w6d1_docker_basics/`.

---

## 7. Assessment

[assessment.md](assessment.md): six reasoning questions, one design-choice explanation, a rubric, and
a 12-minute interview rep (debugging: "the container exits immediately").

---

## 8. Reflection and review

**You should now be able to, without notes:** write a Dockerfile for a Python service with
cache-friendly layer order, an unprivileged user, exec-form command, healthcheck and no secrets; write
a root-anchored `.dockerignore`; publish a port on loopback only; and diagnose "exits immediately",
"not reachable", "not ready" and "slow to stop" from `docker logs`, `docker ps` and `docker inspect`.

**Reflection prompt (5 minutes, in `progress/notes.md`).** Which of your research environments could
you rebuild exactly today, from files alone? What would a Dockerfile for your last paper's analysis
have needed to contain, and what would it still not have captured?

**Retrieval question for later (answer in w6d7 without looking).** A colleague's container takes 10 s
to stop and exits with 137. Name the two independent causes that each produce this, and the one-line
fix for each.

**Next.** [w6d2 - pinned dependencies, multi-stage builds, smoke tests](../w6d2_docker_reproducibility/README.md)
makes this image reproducible next month, measures what a multi-stage build buys here, and adds a
smoke test that CI (w6d3) will run against every image.

---

## Verification record

Executed on 2026-11-22 in the course authoring container: Python 3.13.18, Docker Engine 29.10.0
(BuildKit), base image `python:3.12-slim` (Python 3.12.16, Debian trixie), FastAPI 0.165.0,
uvicorn 0.54.0, pydantic 2.13.5, NumPy 2.5.3, pandas 3.0.5 inside the image.

* `python tools/verify_checks.py lessons/w6d1_docker_basics`: the reference passes the lab (29 static
  checks; the live check is skipped without `WB_DOCKER=1`) and the challenge (15 checks); all 8 lab
  mutants and 5 challenge mutants are rejected, each by the check named in its `MUTANT.md`. The shipped
  starters fail.
* `WB_DOCKER=1 python -m pytest lessons/w6d1_docker_basics/checks -k live` against the reference: passed
  (build, `/readyz`, 300 scores equal to `smoke/expected.json`, UID 10001, stop under 5 s, exit 0).
* A differently written but valid Dockerfile (pip-installs the package, numeric `USER 10001`,
  `ENTRYPOINT` + `CMD`, curl installed for the healthcheck, allow-list `.dockerignore`) also passes the
  lab checks, so they test properties rather than one text.
* The `.dockerignore` matcher agreed with a real `docker build` on the 12-file demo tree.
* `example/run_example.sh` and `example/dockerignore_demo.py --docker`: outputs above.
* The measurements in section 3.2 and `figures/measurements.json` were taken with Docker on a busy
  shared host; the build used `python:3.12-slim` plus the sandbox proxy's CA certificate (an extra
  201 kB layer), substituted with `--build-context`. Your images will be ~0.2 MB smaller.
* Docker behaviour was checked against the Dockerfile reference (moby/buildkit
  `frontend/dockerfile/docs/reference.md`) and docker/docs (build context, best practices, Ubuntu
  install); pages listed in H12.1.
* Not verified: Pop!_OS itself, Podman, Docker Desktop, Python 3.11/3.12 for running the checks
  locally, the time budget.
