# W6D3 challenge — three red runs

`project/` is the `flowguard` service with a CI history that went wrong. `logs/` holds three failing
jobs; `logs/README.md` says what in each log is real and what is reconstructed.

For each log:
1. Find the **first** line that explains the failure.
2. State the cause, and why it appears in CI and not (or not always) on a laptop.
3. Fix it in `project/`. Fix the cause; do not delete the check that caught it.
4. Say how you know the fix works.

Write your answers in `DIAGNOSIS.md` (one `##` section per log, in order: flaky test, cache, image).

## Acceptance criteria

Checked by `python wb.py check w6d3 --challenge`:

* The default `pytest` run of `project/` contains no assertion on elapsed wall-clock time: it passes
  even when the clock is made to run 0.5 s per read, and it still runs the functional tests.
* The latency check is kept, marked `perf` (a registered marker), and run by a workflow that is
  scheduled or manually dispatched and does not trigger on push or pull_request.
* `ci.yml` still caches pip, with a key that can repeat between runs and that tracks a dependency file
  that exists.
* The image job still checks the running service, without calling a tool that the image does not
  contain.
* If `actionlint` is installed, every workflow in `project/.github/workflows/` passes it.
* `DIAGNOSIS.md` has a substantive section for each log that names its cause.

Not checked automatically, but part of the rubric in the assessment: whether your fix is the one you
would defend in a code review, and whether your "evidence" paragraph says what you actually observed.
