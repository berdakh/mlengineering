# w6d7 - retrieval answers

Open only after all twelve questions have a written attempt. Each answer states what a "solid" answer must
contain, then common wrong answers and why they fail.

Written against the final Week 6 lessons on 2026-11-22. Every number is copied from those lessons' authoring
runs (Docker Engine 29.10 on a 4-core authoring machine) or from their synthetic examples, marked
*(SYNTHETIC)*. Section references are to the lesson named in each heading.

## 1. Ten seconds to stop, exit 137 (w6d1, 2.5; section 3.2, figure 1)

`docker stop` sends **SIGTERM** to the container's PID 1, waits **10 s** (default), then sends **SIGKILL**;
exit code 137 = 128 + 9 (SIGKILL). Two independent causes:

1. **Shell-form `CMD`/`ENTRYPOINT`.** PID 1 is `/bin/sh -c "..."`; Debian's `dash` neither forwards SIGTERM to
   its child nor replaces itself with it, so the server never hears the signal. Fix: exec form
   (`CMD ["uvicorn", ...]`), or a wrapper script that ends with `exec uvicorn ...`.
2. **PID 1 installs no SIGTERM handler.** The kernel does not apply default signal actions to a PID
   namespace's PID 1, so a program that relies on the default "terminate on SIGTERM" ignores it in a
   container. Fix: install a handler (`signal.signal(signal.SIGTERM, ...)`), or use a server that has one
   (uvicorn does), or run an init (`docker run --init`).

Measured: exec form stops in **0.5 s** (exit 0, "Finished server process"); either shell form
**10.2-10.4 s** (exit 137). In an orchestrator that restarts containers routinely, the shell form means
dropped in-flight requests and 10 s delays on every deployment.

| Common wrong answer | Why it fails |
|---|---|
| "Increase the stop timeout" | Hides the symptom; requests are still killed mid-flight, just later |
| "137 means out of memory" | 137 is SIGKILL from any source; OOM is one of them (`docker inspect` shows `OOMKilled`), here it is the stop timeout |
| Only one of the two causes | Fixing the exec form does not help a script without a handler as PID 1, and vice versa |

## 2. Layer order, `.dockerignore`, ports (w6d1, 2.3-2.6; figures 2 and 4)

A change to the input of one instruction rebuilds that layer **and every layer after it**: rebuild cost
= Σ<sub>i ≥ k</sub> c<sub>i</sub> for a change hitting layer *k*. Order from rarely to often changing:
`FROM` → `COPY requirements.txt` (or the lock) → `RUN pip install` → `COPY src/` → `COPY models/`. Measured:
a code edit rebuilt in **1.8 s** with dependencies first, **20.9 s** with `COPY . .` before `pip install`.

`.dockerignore` patterns are **anchored at the context root**: `__pycache__` excludes only
`./__pycache__`; every one needs `**/__pycache__`. The robust form is an allow-list (`*`, then `!src`,
`!models`, `!requirements.txt`, then `**/__pycache__`). BuildKit transfers only referenced paths, so with
targeted COPYs a 344 MB pile of local data cost 72 kB; with `COPY . .` it sent 360 MB and the compressed image
grew from 90 MB to 450 MB.

Ports: **inside** the container the server must listen on `0.0.0.0`; `127.0.0.1` there is the container's
own loopback. Symptom measured: `curl: (56) Recv failure: Connection reset by peer` from the host while the
in-container healthcheck still said `healthy`. **On the host**, `-p 8000:8000` publishes on every interface
(anyone on the Wi-Fi can call the model, and Docker-published ports bypass `ufw`); use
`-p 127.0.0.1:8000:8000`.

| Common wrong answer | Why it fails |
|---|---|
| "`.dockerignore` works like `.gitignore`" | Unanchored patterns match at any depth in `.gitignore`, not in `.dockerignore` |
| "Put `--host 127.0.0.1` in the CMD for security" | Makes the service unreachable; restrict exposure with `-p 127.0.0.1:...` on the host instead |
| "Use `--no-cache` to make builds correct" | Correctness comes from the lock; `--no-cache` makes every build pay full cost |

## 3. Build drift, hash-checking mode, what still changes (w6d2, 2.3-2.4; section 8)

| Source of drift | Pin |
|---|---|
| Base image tag | `FROM python:3.12-slim@sha256:...` |
| Direct dependencies | `==` in a lock |
| Transitive dependencies | the whole closure in the lock |
| The file behind a version | `--hash=sha256:...` per distribution file |
| Build cache (an old layer hides that a fresh build would differ) | build from the lock; build without cache regularly in CI |
| apt packages | pin or avoid; prefer Python-only images |

In `pip install --require-hashes -r requirements.lock`, a dependency missing from the lock is **an error, not
a silent resolution** (measured: "all requirements must have their versions pinned with ==" for `starlette`
from a top-level-only lock). Desired, because a silently resolved package is exactly the untested version.
The lab's lock pins 18 packages with 294 hashes.

Behaviour can still change with a fully pinned build: (a) **configuration and inputs outside the image**:
environment variables, a mounted model directory (w6d1, 2.7), data and clients; caught by logging the model
version and configuration at startup, validating configuration (w6d6) and a smoke test against the image as
shipped; (b) **the platform underneath**: CPU instruction set and thread counts change numerical results and
speed (BLAS, OpenMP), the kernel and container runtime differ between hosts; caught by the smoke test's score
comparison with a tolerance and by the scheduled performance lane; (c) a **deliberate update** of the lock or
base digest, which must go through the same smoke test (that is the point of making updates explicit).

| Common wrong answer | Why it fails |
|---|---|
| "`pip freeze` is a lock" | Pins whatever is installed on your platform, without hashes, including tools the service does not need |
| "Fully pinned means byte-identical images" | Timestamps and generated `.pyc` files differ; behaviour is reproducible, bytes are not |
| "Pinned means secure" | Pinned also freezes unpatched vulnerabilities; update on a schedule, through the smoke test |

## 4. Multi-stage builds; the smoke test (w6d2, 2.5-2.6; section 3.3)

Multi-stage builds keep build-time things (compilers, headers, pip caches, source trees, mounted secrets for
private indexes) in a discarded stage; only `/opt/venv` crosses into the runtime image. **Measured: 402 MB
multi-stage against 395 MB single-stage slim.** Not smaller, because every dependency ships as a wheel (the
builder needed nothing extra); the runtime venv lacks pip (about 7 MB) but the lock resolved pandas 3.1.1,
8 MB larger than w6d1's 3.0.5. What shrinks this image: the **base** (`python:3.12` 1.9 GB against `-slim`
0.4 GB) and **the dependency list** (pandas and numpy are 87 % of 172 MB of packages).

The smoke test starts the container, polls `/readyz` until 200 or a timeout, posts a fixed request
(300 SYNTHETIC samples) and compares all scores, decisions and the model version with recorded expectations
(relative 1e-9). It proves: the image starts, loads *this* model, has a working dependency stack, and computes
inside what the package computes outside. It does not prove detection quality, performance under load, or
behaviour on inputs unlike the fixture. Exit codes: **0** pass, **1** wrong answer (look at the model,
dependencies or code), **2** never ready (look at start-up and configuration).

| Common wrong answer | Why it fails |
|---|---|
| "Multi-stage always makes images small" | Only when building needed things running does not; measured here it did not |
| "The smoke test passed, so the model is good" | It checks plumbing on 300 samples it was calibrated on |
| "One exit code for failure is enough" | CI's reader must know whether to look at start-up or at results |

## 5. Gate or scheduled lane; the F1 gate; the flaky timing test (w6d3, 2.5; section 8)

The test: **would a red result on this commit, with no code change, be possible?** If yes (noise, network,
a slow runner, a new day's data), it does not belong in the per-push gate.

The F1 gate fails it twice: (1) F1 on a validation set is an **estimate with sampling noise** (w3d5); a
threshold of 0.01 flips on noise and on data refreshes, so the gate turns red without a regression, gets
lowered or bypassed, and then lets a real regression through; (2) it needs **data** (a download, possibly
secrets) and minutes of evaluation in the gate, which also cannot run on pull requests from forks. Instead:
deterministic unit, API and smoke tests in the gate; a **scheduled evaluation job** on the frozen test set
that reports the metric with an interval and a trend, with an owner who investigates a red run.

Measured: the identical single-request "under 50 ms" test failed **0, 0, 2 and 3 times out of 40** with 0, 2,
4 and 6 competing CPU-bound processes. Same code; a shared runner is a coin with an unknown bias.

| Common wrong answer | Why it fails |
|---|---|
| "Use a looser threshold, e.g. 0.05" | Still a statistical test with an unknown false-alarm rate, in the wrong place |
| "Re-run until green" | A re-run is a diagnostic; a pass on re-run identifies a flaky test to fix or move |

## 6. Four workflow defects; pinning actions; forks (w6d3, 2.2-2.4 and 2.6)

(a) **No `permissions:`**: the job's `GITHUB_TOKEN` gets the repository or organisation default, which may
include write. Fix: `permissions: contents: read` at the top, more per job only where needed.
(b) **`${{ secrets.TOKEN }}` inside `run:`**: expressions are substituted **before** the shell runs, so the
secret becomes part of the generated script (and a transformed secret escapes log masking). Fix: pass it via
`env:` and reference `$TOKEN`; better, keep the gate free of secrets.
(c) **Cache key with `github.sha`**: a new key on every commit, so it never matches an earlier save; every run
misses and stores another unused entry. Fix: key on OS, Python version and a hash of the dependency file
(`setup-python` with `cache: pip` does this). Measured install: 7.0-7.3 s cold, 4.3-4.8 s with a warm pip cache.
(d) **Unquoted versions**: YAML reads `3.10` as the number 3.1. Fix: quote, `["3.10", "3.11"]`.

`@v7` follows the maintainers' moving major tag (fixes arrive; you trust them); a 40-character SHA pins one
commit forever (reproducible, immune to a moved tag; you update it, e.g. via Dependabot); `@main` is a branch
and pins nothing. Forks: GitHub does not give repository secrets to workflows triggered by pull requests from
forks, because the fork's author controls the code that would run; a gate that needs secrets cannot check them.

| Common wrong answer | Why it fails |
|---|---|
| "Secrets are masked in logs, so it is safe" | Masking is string matching; base64 or split output is printed in clear |
| "actionlint passed, so the workflow is fine" | It finds syntax and type errors; the lab's flawed starter passes it |

## 7. Coordinated omission; percentiles (w6d4, 2.2-2.3; worked example)

A **closed-loop** generator (fixed users, each waits for its response) stops sending while the server stalls,
so the requests real clients would have sent never exist and their delays are never measured: **coordinated
omission**. An **open-loop** generator schedules request *i* at *t₀ + i/λ* regardless of responses and measures
latency from the **intended** start.

*(SYNTHETIC)* One 10 ms server, one 1 s stall, about 50 requests/s for 60 s: closed loop **p99 = 10.0 ms**
(one 1,010 ms sample, 0.03 % over 100 ms); open loop **p99 = 710.1 ms**, p99.9 980 ms (3.07 % over 100 ms).

Percentile with linear interpolation: *h = (n − 1)p/100*, *P = x⌊h⌋ + (h − ⌊h⌋)(x⌈h⌉ − x⌊h⌋)*. Care: a p99
from 200 requests is decided by 2 of them (collect thousands); percentiles **do not average** (aggregate raw
latencies or histograms, not per-host p95s). Report p50/p95/p99 at a stated rate, not a mean.

| Common wrong answer | Why it fails |
|---|---|
| "Measure from when the request was actually sent" | That is the measurement coordinated omission corrupts; measure from the intended time |
| "More virtual users fixes a closed loop" | They all stall together; the schedule, not the user count, is the issue |

## 8. Little's law, saturation, workers, a load-independent delay (w6d4, 2.4-2.7, tasks 6-8; section 8)

*L = λW*: requests in the system = arrival rate × time in system, for any stable system. A single-request
worker with service time *S* is busy *ρ = λS*; *n* workers need *n = ⌈λS/ρ*⌉* for a target utilisation *ρ**.
Target 0.6-0.75 because queueing delay grows like *ρ/(1 − ρ)*: about 1 service time at 0.5, 2.3 at 0.7, 9 at 0.9.

One worker served about **83 requests/s** at most. At 90/s p50 was 1,219 ms and the queue grew for the whole
run; at 120/s about 95-97 % of requests timed out at 10 s, served throughput fell to 1.8/s, and RSS went from
90 MB to **2.1-2.8 GB** (2,494 MB in the run quoted).

CPU-bound Python holds the GIL, so more **threads** give more requests in progress, not more completed;
more **worker processes** give more throughput at the cost of a copy of the libraries and model each
(90 MB idle with 1 worker, 220 MB with 2, about 395 MB with 4).

p50 50 ms at both 5 and 100 requests/s with 10 ms server-side: a delay that does not grow with load is not
queueing. Hypotheses: (1) a fixed network-level delay (Nagle meeting delayed ACKs, about 40 ms; the w6d4
finding with `--workers 2`); (2) per-request overhead outside the measured span (new connection, TLS or DNS per
request in the client, a synchronous call to another service, a sleep); (3) the load generator itself (late
starts, its own event loop). Separating measurements: compare client-side latency with the server-side span
for the same requests; look at the **histogram** (a bimodal 10 ms / 50 ms split points to a discrete fixed
delay); change one thing (set `TCP_NODELAY`; reuse connections; check the generator's late-start count). In the
lab, forcing `TCP_NODELAY` cut p50 at 60/s from 52 ms to 9.5 ms.

| Common wrong answer | Why it fails |
|---|---|
| "Add workers until latency drops" | No mechanism; here more workers *introduced* the delay |
| "It's the GIL" | Each worker is a separate process; and the delay did not depend on load |
| "Run at 95 % utilisation to save money" | Queueing delay explodes near 1; one burst and the service collapses |

## 9. Credentials, roles, tags (w6d5, 2.2 and 2.4)

Credentials live only in the AWS CLI's SSO cache on your machine, as **temporary role credentials** from IAM
Identity Center (`aws configure sso` once, `aws sso login` per session). Never: committed to the repository
(including `deploy/config.toml`), baked into an image (anyone who can pull it reads every layer), as plain
environment variables in a task definition (visible to anyone who can describe it; ECS has a separate
`secrets` field), or the root user. `aws sso login` gives credentials that **expire on their own**, behind
browser sign-in and MFA; an access key works until someone deletes it, wherever it was copied.

The **task execution role** lets ECS itself pull the image from ECR and write logs to CloudWatch
(`AmazonECSTaskExecutionRolePolicy`). A **task role** would give the application code AWS permissions; this
service calls no AWS API, so it has none (least privilege).

The tag is the **git SHA** in an **immutable** ECR repository, so "release 1a2b3c4d5e6f" names exactly one
build forever, the deployment record is exact, and rollback has something to point at.

| Common wrong answer | Why it fails |
|---|---|
| "A private repository makes committed keys acceptable" | Repositories get forked, cloned and printed in CI logs; treat a committed key as leaked |
| "Give the task role admin to be safe" | The application needs no AWS access; any permission is attack surface |
| "Tag `latest` and overwrite it" | Mutable tags make "what is running?" unanswerable and rollback impossible |

## 10. Cost, budget, exposure, health check, dry run (w6d5, 2.3, 2.5, 2.8; figures 1-2)

cost ≈ *T*<sub>hours</sub> · *n*<sub>tasks</sub> · (*r*<sub>vCPU</sub>·vCPU + *r*<sub>GB</sub>·GB + *r*<sub>IPv4</sub>)
\+ *r*<sub>ECR</sub>·GB<sub>images</sub> + *r*<sub>logs</sub>·GB<sub>logs</sub>. **Time dominates.** Billed vCPU-hours
of a 0.25 vCPU task: **0.5** (same-day lab), **16** (a weekend), **182.5** (a forgotten month), **365** (two
forgotten tasks). No prices are quoted: they vary by region and date, and the pricing pages were unreachable
when the lesson was written.

The budget alert comes first because the dangerous failure is the forgotten resource, and an alert set up
afterwards does not cover the window in which you forget.

"Not public": the security group has **no inbound rule** by default (the task's public IP exists only to pull
from ECR without a NAT gateway). With `network.allowed_cidr`, only your own address as a `/32`; anything wider
needs `allow_public = true` *and* the public sign-off, otherwise the planner refuses.

The platform health check should probe **`/readyz`** (model loaded), not `/healthz` (process answers);
otherwise a task that cannot serve predictions counts as healthy and is never replaced. The lesson's local runs
answered `/readyz` after 2.9-3.3 s, hence a `startPeriod`.

A dry run proves the plan is what you intend and complete (the live mode runs the same printed text). It does
not prove permissions, quotas, regional availability, or the unresolved `assignPublicIp` question; those are
only tested live, and none of them says whether predictions are correct.

| Common wrong answer | Why it fails |
|---|---|
| "Small task, small bill" | Size multiplies; hours dominate |
| "A public IP means it is reachable" | Reachability is the security group's inbound rules; none by default |
| "Healthy task, working service" | Health checks see readiness, not correctness (week 7) |

## 11. Digests, promotion, rollback versus revert (w6d6, 2.1-2.2, 2.7; incidents 1 and 2)

A **tag** is a name a registry can move (unless the repository is immutable); a **digest** is the hash of the
image manifest and cannot point at different content. Promotion deploys the digest that staging ran
successfully; it **never rebuilds**, because a rebuild is a different artifact: three builds of the same
unchanged source tree gave **three different digests**.

**Rollback** (redeploy the most recent earlier good digest) is right when **the image changed**: incident 1,
a hand-promoted "threshold hotfix" whose `model.json` no longer matched `checksums.json`, so the loader refused
it; rollback to the previous good release restored readiness. It is **wrong when the image did not change**:
incident 2, `FLOWGUARD_MODEL_DIR` changed to `/models/flowguard-z/1.0.1`, a version no image contains. The fix is
to **revert the configuration and redeploy the same digest**; rollback would have picked the older release
`a1b2c3d4e5f6`, which fails with the same environment file and also removes a good release. Rollback is also
unsafe across schema or API changes (expand-then-contract migrations).

| Common wrong answer | Why it fails |
|---|---|
| "Rollback is always the safe first move" | It does nothing for configuration incidents and can undo good releases |
| "Rebuild the same commit for production" | Different bytes; "tested in staging" no longer applies |

## 12. Two validation layers; the memory incident; when a deployment is good (w6d6, 2.3, 2.7; incident 3)

**Startup** validation checks names and formats of `FLOWGUARD_*` variables once and exits (status 2, one JSON
error naming the variable) on a bug that can never fix itself: `FLOWGUARD_MODEL_DlR` (lower-case L) is an
**unknown variable, almost always a typo**, so the container stops at once. **Readiness** handles state: a
missing model directory passes format validation (an absolute path), the process stays up and logs
`model not loaded`, `/readyz` answers 503 and `/healthz` 200, so the platform sends it no traffic.

Memory incident: after a "right-size memory" change (a 64 MiB limit), `/readyz` answered **200 for about 3 s**,
then nothing; the **logs ended on normal startup lines** ("Application startup complete", "Uvicorn running on
http://0.0.0.0:8000"), with no ERROR and no traceback, because the kernel killed the process before it could log.
The service uses about 64 MiB at idle, so the limit left no room (the reference log also notes the second Python
process the health check starts). The cause was visible only in container state:
`docker inspect` showed `exited oom=true exit=137`. Fix: revert the configuration and redeploy the same digest.

A deployment is `good` only when the new version is ready, healthy and **stays** so for a soak period of at
least a few health-check intervals (and ideally through first real traffic), long enough for its likely failure
modes to appear; one successful probe is not enough. Time not ready per incident in the scripted replay:
20, 20 and 13 s.

| Common wrong answer | Why it fails |
|---|---|
| "Validate everything, including file existence, at startup and exit" | A missing model is state; exiting turns it into a crash loop with less evidence than a not-ready service with a clear log |
| "No ERROR line, so the logs are fine" | The OOM kill leaves no log line; container state is evidence logs cannot provide |
| "Ready once, so good" | Incident 3 was ready for 3 s before being killed |
