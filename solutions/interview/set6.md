# Interview set 6 - rubrics (part A) and worked answers (part B)

**Order of use (Weeks 6-8 rule).** Listen to your recording and score it against **part A only**, area
by area, before reading anything else here. Re-record each narrative scored below "Demonstrated". Then
part B.

Reference code: `solutions/interview/set6/c3.py`; wrong answers the tests reject:
`solutions/interview/set6_wrong/`.

Verified in the authoring session (2026-11-22; Python 3.13.18, pytest 9.1.1, numpy 2.5.3):
`SET6_DIR=solutions/interview/set6 python -m pytest interview/set6_tests -q` gives 15 passed in under
1 s; the shipped stub fails all 15; each of the six wrong answers fails at least one test (table at the
end).

**About N1 and N2.** Both services and every number on the evidence cards are **constructed** for the
exercise. The mechanisms are real and were measured in the Week 6 lessons: a model mounted at run time
hides an image that does not contain it (w6d1, 2.7; w6d2, 2.6), and with `--workers 2` uvicorn 0.54
creates the listening socket so that asyncio does not set `TCP_NODELAY`, adding about 40 ms through
Nagle's algorithm and delayed ACKs (w6d4, task 8: p50 52.8 ms with two workers against 10.5 ms with one
at 60 requests/s; 9.5 ms once `TCP_NODELAY` was forced).

Evidence levels per area: **Demonstrated**, **Partial**, **Not yet**.

---

# Part A - rubrics

## N1 - ready on my laptop, 503 in staging (six areas)

**1. Symptom restated precisely**
- [ ] Live but not ready: `/healthz` 200, `/readyz` 503, so the process runs and the model did not load (not a crash, not networking)
- [ ] Asked "what changed?" and challenged "nothing else changed": laptop and staging may not run the same bytes

**2. Hypotheses, named and ordered**
- [ ] At least three distinct hypotheses, for example: (a) the staging image does not contain the model; (b) staging configuration points at a different model path or version; (c) the bundle is present but refused (checksum or format version); (d) resources (memory limit, read-only file system, permissions)
- [ ] Ordered by likelihood *and* cost: reading the startup log first, because the service logs why it is not ready (w6d6: the error names the cause)

**3. The separating observation, asked for deliberately**
- [ ] After N1-1 ("directory not found"): ruled out (c) and the resource hypotheses; asked whether the *same digest* ran on the laptop (N1-2) and what is in the CI-built image (N1-3)
- [ ] Recognised that a locally built image with the same tag is a different artifact (different digest; rebuilds are not byte-identical, w6d6)

**4. Root cause stated as a chain, with evidence for each link**
- [ ] `models/` is git-ignored, so CI's clean checkout has no bundle and the image ships an empty `/app/models`
- [ ] The laptop build context contained the bundle, so the local image worked
- [ ] The CI smoke test **mounts** a fixture model directory over `/app/models` (N1-4), so it tested a model the image does not contain and passed

**5. Mitigation, fix, prevention kept apart**
- [ ] Mitigation: staging keeps (or returns to) the previous good digest; nothing broken reaches production because promotion requires `good` in staging
- [ ] Fix: put the bundle into the build from a versioned source (registry download by version and checksum in the build, or a tracked artifact), not from the developer's working tree
- [ ] Prevention: smoke-test the image **as shipped** (no mounts), add an image check that `load_bundle` succeeds at build time, deploy by digest only, never from a laptop build

**6. Verification**
- [ ] Says how the fix is confirmed: `ls` inside the new CI image shows the bundle; the unmounted smoke test passes; staging `/readyz` 200 and the release history entry `good` after a stable period

## N2 - twice the workers, five times the median latency (six areas)

**1. Symptom restated precisely**
- [ ] Not "it got slower": capacity improved (80 requests/s now served), while *low-load* latency rose by a roughly constant ~40 ms
- [ ] Noted that a latency penalty that **does not grow with load** is not queueing (w6d4, task 8)

**2. Hypotheses, named and ordered**
- [ ] At least three, e.g. (a) CPU contention or thread oversubscription between workers (the team's guess); (b) a fixed per-request delay in the network path (Nagle / delayed ACK, a sleep, DNS, a per-request connection); (c) a load-balancing or connection-handling effect of the multi-process socket; (d) the load generator itself (late starts)
- [ ] Explained why (a) is a poor first bet: contention grows with load and would show in the handler span

**3. The separating observation, asked for deliberately**
- [ ] Asked for server-side versus client-side time (N2-2): handler 3.1 vs 3.2 ms, CPU about a third, `OMP_NUM_THREADS=1` → the extra time is outside the handler; (a) is out
- [ ] Asked for the distribution (N2-3): bimodal, most requests near 50 ms, a minority near 10 ms → a discrete, fixed delay hitting most requests; the size (~40 ms) matches the delayed-ACK timer

**4. Root cause stated, with the mechanism**
- [ ] Nagle's algorithm on the response socket holds the last segment until the client's (delayed) ACK; servers normally disable it with `TCP_NODELAY`
- [ ] Why only with two workers: the multi-worker path creates the listening socket in a way that leaves `TCP_NODELAY` unset (one worker lets the event loop create the socket, which sets it); N2-4 is the decisive experiment

**5. Decision for the launch**
- [ ] Ship two workers **with** the socket fix (or a server configuration that sets `TCP_NODELAY`), re-measured open loop against the stated budget; not "go back to one worker", which fails at 80 requests/s
- [ ] Named the risk of the fix (relying on a server's internal API, as w6d4's `serve.py` does) and how it is contained: a test that measures p50 at low load in the scheduled performance lane, pinned server version

**6. Communication**
- [ ] Answered the team's question directly ("no, the workers are not fighting for CPU; here is the evidence") and reported percentiles at stated rates, not averages

## C3 - code and two spoken answers

- [ ] `python -m pytest interview/set6_tests -q`: 15 passed within the 20 minutes
- [ ] Before coding: p95 over 2xx describes how long successful work takes; failed requests can be very fast (an immediate 503) or very slow (a 10 s timeout) and would distort it either way, while the error rate must count every request (w6d4, 2.1-2.2 and task 4)
- [ ] After coding: memory is O(number of 2xx records in the window per endpoint) for the durations, plus O(1) per line; for a 10 GB log stream the lines (do not `readlines()`), pre-filter by time, and replace exact percentiles by a fixed-bucket histogram or a quantile sketch per endpoint (approximate p95 with a stated error), or push the aggregation to the log store

---

# Part B - worked answers

## N1 - a strong answer, compressed

"Live but not ready means the process is up and the model did not load, so I start with the service's own
startup log, not with the network or the platform. Before that, one question: is staging running the same
bytes as your laptop? You said the same *tag*; a laptop build with the same tag is a different image.

*(N1-1)* 'Model directory not found' at the configured path. That rules out a refused bundle (that would
say checksum or format) and permissions (that would say permission denied). Remaining: the path is wrong
for this image, or the image has no model. The path matches the version this release expects, so I want
to see inside the image staging runs, and how your laptop image was built.

*(N1-2)* Different digests: your laptop image was built from your working tree; staging runs CI's push.
*(N1-3)* CI's image has an empty `/app/models`, and `models/` is git-ignored, so the bundle never reaches
CI's checkout. Your working tree has it, so your local build worked.

Then why did CI's smoke test pass? *(N1-4)* It mounts a fixture model over `/app/models`. The smoke test
proved that *the code* can load *a* model; it never tested the image we ship.

Mitigation: staging stays on the previous good digest; promotion rules keep this out of production. Fix:
the build obtains the bundle from a versioned source with its checksum, not from someone's working tree.
Prevention: smoke-test the image exactly as shipped, with no mounts; add a build step that loads the
bundle; deploy by digest only. Verification: `ls` in the new image shows the bundle, the unmounted smoke
test passes in CI, staging is ready and stays ready for a few health-check periods, and the history records
it as good."

**Common weak answers.** Restarting the staging container, or redeploying the same digest, before reading
the log (changes state, gathers no evidence). Debugging the load balancer or ports (the service answered
`/healthz`, so it is reachable). Stopping at "add the model to the image" without explaining why the smoke
test passed, which is the defect that let it through.

## N2 - a strong answer, compressed

"Capacity improved, so the second worker is doing useful work. What got worse is low-load latency, and
by about the same 40 ms at 10 and at 40 requests/s. Queueing grows with load; a constant offset is a fixed
delay somewhere. So the team's CPU-contention hypothesis is possible but not my first bet: contention
would grow with load and show up in the handler's own time. I want server-side timing next to the client's.

*(N2-2)* Handler 3.2 ms in both configurations, CPU about a third, `OMP_NUM_THREADS=1`: the extra 40 ms is
outside the application code. Candidates: something per request in the network path. *(N2-3)* The
distribution is bimodal: a fifth of requests at about 10 ms, most at about 50. A fixed, discrete delay that
hits most requests, about 40 ms: that is the signature of Nagle's algorithm interacting with delayed ACKs.
Servers disable Nagle with `TCP_NODELAY`; the question is why only the two-worker mode loses it.

*(N2-4)* Setting `TCP_NODELAY` on the listening socket removes the penalty with two workers and does
nothing with one. So in multi-worker mode the server creates the socket without the option that the
single-worker path gets from the event loop.

For the launch: two workers with the socket fix, re-measured open loop at the launch rate against the
budget; not one worker, which saturates before 80 requests/s. The fix touches server internals, so I
would pin the server version and add a scheduled performance check of p50 at low load, so an upgrade that
changes this is caught. And I'd report percentiles at stated rates, because the mean hid the two modes."

**Common weak answers.** Raising or lowering workers until it looks better (no mechanism, and fails one of
the two loads). Blaming the GIL (each worker is a separate process with its own interpreter). Reporting
mean latency. Concluding from one load level.

## C3 - notes on the reference

* `datetime.fromisoformat` parses offsets (Python 3.11+ also accepts a trailing `Z`); subtracting two
  aware datetimes compares instants, which is what rule 1 needs. Comparing timestamp *strings* only works
  when every line uses the same offset and the same precision.
* The window test is `0 <= end - ts < window_s` on the age, which is exactly `end - window_s < ts <= end`.
  Half-open windows make consecutive windows partition the records.
* Parsing raises `ValueError` for anything malformed and the loop counts it; a single `try` around
  `json.loads` alone would still crash on `{"ts": null}` or a string status.
* `bool` is rejected explicitly because `True` is an `int` in Python.
* Percentile: `h = (n - 1) * q / 100`, interpolate between `floor(h)` and `ceil(h)`; equals
  `numpy.percentile` with its default method.

## C3 wrong answers and the tests that reject them

| Wrong answer (`solutions/interview/set6_wrong/`) | What it does | Result (authoring run) |
|---|---|---|
| `c3_4xx_as_errors` | counts `status >= 400` as errors | 1 failed, 14 passed |
| `c3_p95_all_statuses` | p95 over every request, including 4xx and 5xx | 1 failed, 14 passed |
| `c3_nearest_rank` | nearest-rank percentile instead of linear interpolation | 2 failed, 13 passed |
| `c3_string_timestamps` | drops the offset and compares wall-clock times | 1 failed, 14 passed |
| `c3_crash_on_bad_line` | lets one malformed line raise | 1 failed, 14 passed |
| `c3_inclusive_start` | includes a record exactly `window_s` old | 1 failed, 14 passed |

Command used for each: `SET6_DIR=solutions/interview/set6_wrong/<name> python -m pytest interview/set6_tests -q`.
The timezone test was strengthened during authoring: its first version used two records whose naive and
offset-aware counts happened to agree, and `c3_string_timestamps` passed it.
