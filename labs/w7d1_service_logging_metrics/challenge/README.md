# W7D1 challenge: SLOs you can defend

**Task.** Define service level objectives for the `flowguard` prediction API and implement the arithmetic
that turns them into an error budget and a paging decision. Work alone; the hints are in `../hints/`,
but this challenge only counts as independent if you do not open hint 3.

## Part A: `slo.py` (auto-graded)

Implement the five functions in `slo.py`. Their inputs are the JSON access events your lab writes
(`event == "access"`, with `route`, `status`, `duration_ms`). The module docstring of the starter gives
the definitions; in short:

* `availability_sli(events) -> (good, valid)` over `/predict` access events. Decide (and the checks
  enforce) which statuses are not the service's fault.
* `latency_sli(events, threshold_ms) -> (good, valid)`. Decide which requests are valid for a latency SLI.
* `error_budget(target, valid)`, `burn_rate(bad, valid, target)`.
* `should_page(window_counts, target, rules)`: the multi-window rule of the lesson, section 2.5.

## Part B: `SLO.md` (rubric-graded)

Fill the six sections of the template. Use numbers: a traffic assumption, targets, a worked budget,
windows and burn-rate factors. Justify each choice from what the plant engineer needs and from what you
measured in w6d4 and in this lesson's replay; say what the SLOs do not cover.

## Acceptance criteria

* `python wb.py check w7d1 --challenge` passes.
* `SLO.md` scores at least "meets" on every row of the SLO rubric in `../assessment.md`.
