# w5d5 assessment — model answers

## 1. 95 % coverage, 7 of 12 defects killed

Coverage counts lines *executed*; a defect is killed only when an *assertion* depends on the line's
result. A status-code-only suite executes the scoring, threshold and response-building lines on
every 200 request, so coverage is high, but it never looks at the numbers: signed scores, a strict
threshold, the sample std, a missing model version and the concurrency race all leave the status at
200 (Figure 2: 7/12). Two kinds of assertion close the gap: **content assertions** (exact expected
scores, flags, version for constructed inputs, including a negative value, a value exactly at the
threshold, and a burn-in where ddof matters) and a **concurrency assertion** (many distinct requests
in parallel, each response matching its own request).

*Common wrong answer:* "add more tests". More tests of the same kind (more status codes) do not kill
content defects.

## 2. TestClient without `with`

The lifespan (startup and shutdown) runs only when `TestClient` is used as a context manager. Without
`with`, `create_app` has built the routes but never loaded the bundle, so `app.state.model` is `None`:
exactly the state of a real process between "started" and "ready". That makes it a free, deterministic
test of the readiness contract: `/readyz` must be 503 in that state. The pitfall is writing *other*
tests without `with` and then concluding the service is broken (or, worse, adjusting expectations).

## 3. 500 instead of 422 for NaN

Client: 422 means "your request is invalid; do not retry it unchanged"; 500 means "server fault; a
retry may succeed". A client with retry-on-5xx will resend the same poisoned request several times,
multiplying load and delaying its own error handling. Operators: 5xx responses count against the
service's error budget and page the on-call engineer (w7d1); bad client input should not page anyone.
Also, the 500 here comes from a second failure (serialising NaN), which hides the first one in the logs.

## 4. Race test passes 1 run in 50

The test is not wrong; a passing concurrency test is weak evidence, a failing one is strong evidence.
To make it more sensitive: more requests, more threads, distinct values per request, and keep the
per-request work small so requests overlap. But races are best removed by design: the review checklist
should flag any write to module-level, app-level or model-level state inside a request handler, and
any cache must be keyed by request content and safe for concurrent use (or per request).

*Common wrong answer:* "mark it flaky and rerun". That hides the 1-in-50 production failure the test
is reporting.

## 5. ddof=1 is a defect

The contract is training/serving parity: the threshold was chosen in w4d5 on scores computed with the
population std (ddof 0). The sample std is larger by sqrt(n/(n-1)), so served scores are smaller than
training scores and the alert threshold silently becomes less sensitive. The difference is largest
when n is small: with two burn-in values it is a factor sqrt(2) = 1.414 (burn-in `[0, 2]`: score 3 vs
2.12), with 100 values about 0.5 %, which a loose tolerance might not see. Which test caught it: the
test with burn-in `[0.0, 2.0]` asserting score 3.0 for value 4.0 (`test_population_std_is_used`).

## 6. v1 -> v2

Breaking: `site_id` newly required (every v1 request gets 422); `scores` renamed to `score` (a removed
response field; v1 clients read a missing key); `burn_in` `maxItems` 3600 -> 600 (v1 requests with long
calibrations now get 422). Compatible: `explain` (optional, defaults to the old behaviour), `latency_ms`
(new response field; clients ignore unknown fields), `GET /sites` (new endpoint), `version` changes.

`T -> T | None`: in a request the server now accepts *more* (old clients never send `null`, so they are
unaffected); in a response the server may now *return* `null`, which an old client does not expect
(a `float(value)` call fails). Compatibility is about what the other side sends or reads.

## Design choice: start degraded vs crash

**For degraded start:** the process stays observable: `/healthz` and `/readyz` explain the failure
(`reason`), logs and metrics keep flowing, and the orchestrator simply does not route traffic to an
unready instance. In a rolling deployment the old version keeps serving; the new one sits unready and
the rollout stalls visibly instead of crash-looping. It also allows loading a model later (hot reload)
without restarting the process.

**For crashing:** a missing or corrupt bundle is a deployment error that will not fix itself; failing
fast makes the deploy fail immediately and loudly, and avoids a fleet of processes that look alive
but never serve. A degraded instance that nobody alerts on is worse than a crash.

**Setting decides:** with an orchestrator that uses readiness probes, alerts on "unready for > N
minutes" and does rolling updates (Kubernetes, ECS with health checks), degraded start is better. With
a plain process supervisor, no readiness checks, or a batch job, crashing is better, because nothing
would ever notice the unready state.

## Interview rep: the flaky suite

**Hypotheses, cheapest first.** (1) Order dependence through shared state: run the failing test alone
(`-k scores`): it passes, so another test changes something it relies on. (2) A timing issue in the
lifespan: rerun the single test several times; it always passes, so timing is unlikely.

**Cause.** `BUNDLE` is created once at import time in a module-level temporary directory and shared by
both tests. `test_tampered_bundle_is_not_ready` edits `model.json` in place, so every later test loads
a bundle whose checksum no longer matches: the service (correctly) refuses it and `/predict` answers
503. Alone, `test_scores` sees the original bundle and passes. (Failure observed in the authoring run:
`assert 503 == 200`.)

**Fix.** A fixture that builds a fresh bundle in `tmp_path` per test
(`solutions/labs/w5d5_api_testing/interview_rep/test_flaky_fixed.py`, 2 passed). Do not "fix" it by
reordering tests or by restoring the file at the end of the tampering test: the next failure mode
(an exception before the restore) would bring the flakiness back.

**General rule.** Tests must not share mutable state; each test creates what it changes. **Safeguards:**
run tests in random order with a plugin such as `pytest-randomly` (not installed or tested here; named
from memory),
run each test file in isolation in CI occasionally, and avoid module-level setup that writes files.

## Rubric notes

A level-3 answer to question 4 separates *detection* (the test) from *prevention* (design and review).
A level-3 debugging narrative states hypotheses before running anything, uses `-k` to bisect, and
names a rule that would have prevented the bug, not only the fix.
