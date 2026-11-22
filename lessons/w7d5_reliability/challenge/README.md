# W7D5 challenge: flowguard's failure-mode table and two mitigations

Independent work. No solution is given here; the reference is in `solutions/` for after you finish.

## Part 1 — failure-mode table (`FMEA.md`)

Fill in `challenge/FMEA.md` for the whole flowguard system as it stands after Week 7: the API, the
streaming path (w5d3), the artifact and registry (w5d2), the container and deployment (w6). One row per
failure mode, columns exactly:

| Failure | Category | Detection | Impact | Mitigation | Test |

* **Category** is one of `input`, `model`, `artifact`, `dependency`, `resource`, `stream`, `deployment`.
* **Detection**: the concrete signal (metric, log event, status code, probe) and who sees it.
* **Impact**: what goes wrong for the caller or the plant, with a severity 1-4 (see lesson 2.8).
* **Mitigation**: what the system does, not what a person hopes to do.
* **Test**: the test or drill that produces this failure on purpose (name it). "None yet" is allowed in
  the text only if the row also says what test you would write.

**Acceptance criteria (automated):** the header row exactly as above; at least 10 rows; no `TODO`; every
category valid; at least one row each for input, model or artifact, dependency, resource and stream; every
Test cell names a test or a drill; the two mitigations of part 2 appear in the table.
**Reviewed by hand:** whether the severities are argued and the detections would actually fire.

## Part 2 — two mitigations (`resilience.py`)

Implement both classes in `challenge/resilience.py`, keeping the interfaces.

**`CircuitBreaker(failure_threshold=5, reset_timeout=30.0, clock=time.monotonic)`** with `.state` and
`.call(fn, *args, **kwargs)`:

* `closed`: calls pass through; results and exceptions are returned or raised unchanged;
  `failure_threshold` **consecutive** failures open the circuit (a success resets the count).
* `open`: `call` raises `CircuitOpen` without calling `fn`, until `reset_timeout` seconds (by `clock`)
  have passed since opening; then the state is `half_open`.
* `half_open`: exactly one trial call is let through. Success closes the circuit; failure re-opens it and
  restarts the timeout. Any other call while the trial is running raises `CircuitOpen`.

**`SampleOrderGuard(max_gap_s)`** with `.check(machine_id, timestamp) -> str`, per machine:

* first sample of a machine: `"ok"`;
* same timestamp as the last accepted sample: `"duplicate"` (state unchanged);
* older than the last accepted sample: `"out_of_order"` (state unchanged);
* more than `max_gap_s` after the last accepted sample: `"gap"` (accepted; the caller restarts burn-in);
  a difference of exactly `max_gap_s` is `"ok"`;
* otherwise `"ok"` (accepted). Machines never affect each other.

**Acceptance criteria (automated):** `python wb.py check w7d5 --challenge` passes. The checks use a fake
clock; your breaker must read time only through `clock`.

**Stretch (not graded):** wire the `SampleOrderGuard` in front of your w5d3 `StreamScorer` and the breaker
around a call to an imaginary feature service, each with a counter and a test.
