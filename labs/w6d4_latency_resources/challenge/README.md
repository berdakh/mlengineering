# W6D4 challenge — a capacity plan you can defend

**Scenario.** The plant operator wants `flowguard` for its whole fleet: **120,000 machines**, each
sending one 600-sample request every 10 minutes. Requests are not evenly spread: after a shift change
many machines flush at once, and the operator's data team estimates the peak at **3 times the average**.
The service-level objective (SLO) for `/predict`: **p95 latency <= 100 ms and error rate <= 0.1 %**,
measured at the service. Hosts have 4 vCPUs.

You have one real measurement: `measured_curve.csv`, the single-worker service on the authoring
machine (means of two repetitions of `lab/measure_service.py --workers 1`, 600-sample requests,
open-loop load from the same 4-core machine). Columns: offered rate, p50/p95/p99/mean latency (ms),
error rate, achieved throughput.

## Tasks

1. Implement the four functions in `capacity.py` (`load_curve` is given). Their docstrings are the spec.
2. Write `CAPACITY.md`, a one-page capacity plan with these sections (headings must contain the words):
   * `## Assumptions`: traffic model (average and peak rates you derived, and how), the service time you
     used and where it comes from in the curve, the utilisation target and why, what the measurement
     setup over- or under-states.
   * `## Calculation`: Little's law at peak, workers needed, hosts needed; show the numbers.
   * `## Sensitivity`: how the answer moves if traffic is 0.5x / 1.5x / 2x your estimate and if you use a
     tail latency instead of the mean as service time; which assumption matters most.
   * `## Risks`: at least three, with what you would measure to retire each.
   State your recommendation as a number of workers (for example "11 workers").

## Acceptance criteria (`python wb.py check w6d4 --challenge`)

* `littles_law_concurrency`, `workers_needed`, `max_rate_within_slo` and `sensitivity` give the right
  numbers on test cases (including units, rounding, and rates that pass after a failure).
* `load_curve("measured_curve.csv")` works with your `max_rate_within_slo`.
* `CAPACITY.md` has the four sections, states a number of workers and is at least 250 words.

The numbers are checked automatically; the reasoning is graded with the rubric in the assessment.
