# Interview set 6 - two debugging narratives, timed; log arithmetic in code

**Use on:** the Week 6 review day (`w6d7`). **Total time: 45 minutes, timer on.**
**Conditions (Weeks 6-8 level):** timed; the narratives are **spoken aloud and recorded** (phone voice memo
is enough); no hints, no solutions, no AI assistance. **Score yourself against the rubric
(`solutions/interview/set6.md`, part A) before reading anything else in that file.** Part B, the worked
answers, stays closed until you have re-recorded every narrative scored below "Demonstrated".

| # | Type | Time |
|---|---|---|
| N1 | Debugging narrative: ready on my laptop, 503 in staging | 12 min |
| N2 | Debugging narrative: twice the workers, five times the median latency | 12 min |
| C3 | Coding: per-endpoint p95 and error rate over a sliding window of JSON logs | 20 min |

On a short day: N1 and C3 (32 minutes).

The services and evidence in N1 and N2 are **constructed for practice** (not measurements of a real
system); the mechanisms behind them are the ones measured in this week's lessons.

**How a debugging round is judged.** Not on reaching the root cause first. An interviewer listens for
whether you (1) restate the symptom precisely and ask what changed, (2) name several hypotheses and
order them by likelihood *and* cost of checking, (3) choose the one observation that best separates the
leading hypotheses, (4) update on each piece of evidence instead of defending your first guess,
(5) distinguish mitigation (stop the bleeding) from fix (remove the cause) from prevention, and (6) say
how you would know the fix worked.

**How to use the evidence cards.** Each narrative has numbered evidence cards below it. Before you read a
card, say aloud your current hypotheses (most likely first) and *which card you ask for and why*. Then
read only that card. A real interviewer answers the question you ask; reading the cards in order is
allowed, but say what you would have asked for first. Treat each card as what the interviewer tells you.

---

## N1 - "Ready on my laptop, 503 in staging" (12 minutes)

A teammate on a sensor-analytics team (not `flowguard`; a vibration-classification service with the
same structure) hands you this on a Monday:

> "The new image builds in CI, CI's smoke test passes, and when I run the image on my laptop `/readyz`
> says 200. We deployed the exact tag CI built to staging and `/readyz` answers 503. `/healthz` answers
> 200. Nothing else changed. Can you look?"

Talk through what you would do. Keep about 2 minutes at the end for: *"How do we stop this from
reaching staging again?"*

**Evidence card N1-1 (staging logs, access lines filtered out).**

```
{"level": "INFO",  "logger": "vib.serve", "msg": "starting vib 2.3.0", "release": "9e41c0aa77d2", "model_dir": "/app/models/vib/4.1.0"}
{"level": "ERROR", "logger": "vib.api",   "msg": "model not loaded: model directory not found: /app/models/vib/4.1.0", "release": "9e41c0aa77d2"}
```

**Evidence card N1-2 (what "the image on my laptop" was).**

```
$ docker images vib --digests      # on the teammate's laptop
REPOSITORY  TAG            DIGEST                  CREATED
vib         9e41c0aa77d2   sha256:5c1d0e...        2 hours ago      # built locally with: docker build -t vib:9e41c0aa77d2 .
$ # staging runs   registry.example/vib@sha256:a7f3b2...           # pushed by CI
```

**Evidence card N1-3 (inside the CI-built image).**

```
$ docker run --rm --entrypoint ls registry.example/vib@sha256:a7f3b2... -la /app/models
total 0
$ git check-ignore -v models/vib/4.1.0/model.json
.gitignore:7:models/    models/vib/4.1.0/model.json
```

**Evidence card N1-4 (the CI smoke-test step).**

```yaml
- name: Smoke test
  run: |
    docker run -d --name smoke -p 127.0.0.1:8000:8000 \
      -v "$PWD/tests/fixtures/models:/app/models:ro" vib:${{ github.sha }}
    python scripts/smoke_test.py http://127.0.0.1:8000
```

---

## N2 - "Twice the workers, five times the median latency" (12 minutes)

An inference service for text classification (Python, FastAPI, uvicorn, CPU only, a scikit-learn
linear model on hashed features) ran with one uvicorn worker. Before a product launch, the team changed
the start command from `uvicorn app:app --workers 1` to `--workers 2` to handle more traffic. Then:

> "Our load test got *better* at high load, but at normal load the median went from about 10 ms to about
> 50 ms. The model hasn't changed. Is the second worker fighting the first for CPU?"

Talk through what you would do. Keep about 2 minutes at the end for: *"Would you ship `--workers 2`
for the launch? What exactly would you change first?"*

**Evidence card N2-1 (the team's open-loop load test, 2 x 30 s per point, p50 / p95 in ms).**

| Rate (requests/s) | `--workers 1` | `--workers 2` |
|---|---|---|
| 10 | 9.7 / 14.1 | 10.4 / 51.8 |
| 40 | 9.9 / 28.3 | 50.6 / 57.4 |
| 80 | 1,180 / 2,950 (queue grows) | 51.9 / 79.5 |

**Evidence card N2-2 (server-side timing logged by the app for the same runs).**

```
handler span, median over all requests:  --workers 1: 3.1 ms   --workers 2: 3.2 ms
host CPU at 40 requests/s:               --workers 1: 34 %     --workers 2: 31 %  (4 cores)
OMP_NUM_THREADS=1 is set in both runs
```

**Evidence card N2-3 (latency histogram at 40 requests/s, `--workers 2`).**

```
  0-15 ms  ##########            19 %
 15-40 ms  #                      2 %
 40-60 ms  ###################################### 77 %
   >60 ms  #                      2 %
```

**Evidence card N2-4 (an experiment the team ran on request).** With `--workers 2`, a two-line change
that sets the socket option `TCP_NODELAY` on the listening socket before the workers start gives p50 /
p95 of 9.8 / 13.0 ms at 40 requests/s. With `--workers 1` the same change makes no difference.

---

## C3 - Per-endpoint p95 and error rate over a sliding window (20 minutes)

Implement `window_summary(lines, end, window_s=300.0)` in `interview/set6_work/c3.py`. Standard library
only. It is the computation behind an on-call question such as "what did `/predict` look like in the five
minutes before the alert?".

**Input.** `lines` is any iterable of strings (it may be a generator you can read only once), one JSON
object per line, as a structured logger writes them. A **request record** looks like:

```json
{"ts": "2026-03-10T10:04:58.120+00:00", "level": "INFO", "event": "request",
 "path": "/predict?batch=1", "status": 200, "duration_ms": 11.4}
```

`end` is an ISO 8601 timestamp **with** a UTC offset, e.g. `"2026-03-10T10:05:00+00:00"`.

**Rules.**

1. A record counts if `end - window_s < ts <= end`, comparing instants (offsets matter: `11:04:30+01:00`
   is `10:04:30Z`). Lines are not necessarily in time order.
2. Group by `path` with any query string removed (`/predict?batch=1` → `/predict`).
3. Per endpoint report `count` (requests in the window), `error_rate` (share with `status >= 500`; a 4xx
   is the client's error, not the service's) and `p95_ms` (95th percentile of `duration_ms` over requests
   with `200 <= status < 300`, using linear interpolation between closest ranks, i.e. numpy's default;
   `None` if there are none).
4. Lines whose `event` is not `"request"` (deploys, `model_loaded`, ...) are ignored silently.
5. Blank lines are ignored. Any other line that is not a valid request record is **counted in `skipped`
   and never raises**: not JSON, not an object, a missing field, a timestamp without an offset, a status
   that is not an integer, a duration that is not a finite non-negative number.
6. Return `{"endpoints": {path: {"count": int, "error_rate": float, "p95_ms": float | None}},
   "skipped": int}`. It must be JSON-serialisable.

Before coding, say why p95 is taken over 2xx only while the error rate is over everything (w6d4).
After coding, say what your function's memory use is as a function of the number of lines, and what you
would change to run it over a 10 GB log.

```bash
python -m pytest interview/set6_tests -q
```

The harness loads your file as a module named `set6_c3`. A worked check: twenty `/predict` requests in the
window with durations 1, 2, ..., 20 ms give `p95_ms = 19.05`.
