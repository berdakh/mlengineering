# Problem statement: `flowguard` (reference answer)

Educational prototype on laboratory testbed recordings (SKAB v0.9). The stakeholder is a
role-play; no claim is made about any real plant. Assumptions are marked **[assumed]**.

## Decision supported

A reliability engineer responsible for a water-circulation loop decides, while the loop is running,
whether to **go and inspect it now**. The system raises an alert; the engineer acts. Nothing is
actuated automatically. Without the system the engineer finds faults on scheduled rounds
**[assumed: every few hours]** or when a hard limit trips.

## Unit of prediction

One anomaly score per **timestamp (about 1 s) per loop**, computed from that loop's sensor values up
to and including that timestamp. The unit of *decision* is coarser: an **alert**, raised when the
score stays above a threshold, at most one per abnormal episode. The unit of *generalisation* is the
**experiment** (one continuous recording with one fault episode): a deployed model always meets a
recording it has not seen.

## Prediction time and horizon

Prediction time is "now", online. There is no forecast horizon: the task is detection of a condition
that has already begun, and the quantity that matters is **delay from onset to alert**. Features may
use the past of the same recording only; nothing after the timestamp, and no statistic computed over
the whole recording.

## Label definition

`anomaly = 1` for samples inside the period in which the experimenters induced a fault (valve
closing, leak, rotor imbalance, cavitation ...); `changepoint = 1` at the marked transitions. Labels
come from the experiment protocol, so they mark **when the cause was applied**, which is not when
the sensors first show it; the first seconds of a "positive" segment may be indistinguishable from
normal, and that bounds achievable point-level recall. Each recording has exactly one positive
segment, so there are **34 events** in total. An *event* is one contiguous positive segment. In a
real plant the label would instead come from maintenance records, arriving days later and only for
faults somebody found.

## Cost of errors

* **Missed event** (no alert during the segment): the fault continues until the next round;
  possible equipment damage. Treated as the expensive error.
* **Late alert:** cost grows with delay; an alert in the last seconds of a segment is nearly a miss.
* **False alert** during normal operation: a wasted inspection **[assumed: about 15 minutes]** and,
  more importantly, erosion of trust; operators mute systems that cry wolf.
* Working assumption to be challenged: a missed event costs on the order of **ten** false alerts,
  and more than about **one false alert per hour** of normal operation makes the system unusable
  **[assumed]**. The threshold is chosen under that false-alert budget, not by maximising F1.

## Constraints

* Causal, online scoring; latency per sample far below the 1 s sampling interval on a CPU.
* Cold start: a new recording has no history, so a warm-up period without scores must be defined.
* Only the eight logged sensors; no maintenance history, no set-points.
* The engineer must be able to see *which sensors* drove an alert; a score alone is not actionable.
* Small data: 34 labelled recordings, three fault families, one testbed. No result transfers to
  another installation without re-validation.

## Success metrics

Chain from need to offline proxy:

1. Business: fewer undetected fault-hours, at tolerable inspection cost (not measurable here).
2. Operational proxy: **event recall** and **median detection delay** at a threshold that gives at
   most the budgeted **false alerts per hour** on normal operation.
3. Model-development proxy: point-level **PR-AUC** (threshold-free, cheap to compute), used for
   iteration only and always reported next to the event-level numbers.

Sample-level prevalence is about 35 %, so accuracy and ROC-AUC flatter every method; neither is a
headline metric. With 34 events, every event-level figure is reported with an experiment-level
bootstrap interval, and differences inside the interval are not claimed.

## Baseline

* **Do nothing:** event recall 0, no false alerts. The reference point for "is any alerting worth it".
* **Simple rule an engineer would write:** per-sensor limits from the fault-free recording (mean
  plus or minus k standard deviations), alert if any sensor is outside for several consecutive seconds.
* A learned model must beat the simple rule by more than the bootstrap uncertainty to justify itself.

## Splits

Frozen in `splits/v1.json` (seed 0). Unit: experiment. **Test:** 9 whole experiments, stratified by
family (4 `valve1`, 1 `valve2`, 4 `other`), opened only for final reporting. **Development:** the
other 25 experiments in 4 grouped folds (7/6/6/6). **Reference normal:** the fault-free recording,
for fitting detectors that learn "normal"; never scored for recall. **Protocol B:** train on
`valve1` + `valve2`, evaluate on all of `other`, to estimate behaviour on fault mechanisms never
seen in training. The manifest does not change after the first result is computed; a new split is a
new version (`v2`) and all results are recomputed and relabelled.

## Out of scope

Fault diagnosis (which fault), remaining-useful-life prediction, forecasting sensor values as a
goal in itself, automatic shutdown, and any claim of validity outside this testbed.
