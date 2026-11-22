# Decision memo: which detector flowguard ships

Author: reference solution · Date: 2026-11-22 · Decision owner: reliability engineer, testbed loop ·
Status: final for milestone 1

## Context

flowguard raises alarms when the circulation loop leaves normal operation. We must choose one
detector to build the Week 5 service around. These were fixed before any comparison: MPID +0.05
point-level PR-AUC; alert budget of 1 false alarm per 8 h of normal operation; p95 scoring latency of
at most 20 ms per sample. The complexity ranking, simplest first, is: one sensor, no training; eight
sensors, no training; a tree ensemble per run; a model trained on labelled faults.

## Options

1. **flow-rate |z|**: distance of one sensor from its start-up level (reference).
2. **Mahalanobis**: joint distance over eight sensors.
3. **Isolation forest**: 100 random trees per run.
4. **Logistic (supervised)**: trained on labelled development faults.
5. Do not ship a detector yet; collect more labelled faults first.

## Evidence

Development data: 27 experiments in 23 clusters (files that share rows form one cluster). 95 %
paired cluster-bootstrap intervals; operating point chosen on development data for the alert budget.

| Candidate | PR-AUC [CI] | Δ vs flow-rate [CI] | Reading | Events at budget | p95 ms | Size | Retrain needs |
|---|---|---|---|---|---|---|---|
| flow-rate \|z\| | 0.765 [0.680, 0.845] | reference | - | 11/27 | 0.24 | 370 B | 100 normal rows |
| Mahalanobis | 0.705 [0.597, 0.800] | -0.060 [-0.212, +0.071] | inconclusive | 8/27 | 0.27 | 920 B | 100 normal rows |
| Isolation forest | 0.562 [0.491, 0.639] | -0.203 [-0.299, -0.120] | worse | 3/27 | 5.31 | 759 kB | 100 normal rows |
| Logistic | 0.834 [0.762, 0.895] | +0.069 [+0.022, +0.128] | inconclusive | 13/27 | 0.42 | 1 kB | labelled faults |

All candidates meet the latency budget. All raised zero false alarms at the budget on development
data, and every one detected fewer than half of the development events at that strict operating
point. The Pareto front (PR-AUC, false alarms per hour, p95 latency) is flow-rate |z| and logistic.

## Decision

**Ship flow-rate |z|.** The rule fixed in advance was: among the candidates that meet the hard
constraints, take the simplest one shown practically better than the reference. If none is, take
the simplest one not shown worse. No candidate is shown practically better: the logistic gain of
+0.069 has an interval reaching down to +0.022, below the MPID. So the simplest candidate wins.

The single test look, at the frozen operating point (7 experiments): PR-AUC 0.884; 5 of 7 events
detected (Wilson 95 % [0.36, 0.92]); no false alarms; median delay 100 s.

## Risks

* **We may be leaving a real gain unused.** The logistic model may truly be about 0.07 better. We
  would notice through accumulated labelled faults; the comparison is rerun at milestone 4.
* **One sensor is blind to faults that do not move flow rate.** We would notice in the per-family
  error analysis (w3d6) and in post-incident reviews of missed faults. The Mahalanobis score can be
  logged alongside as a shadow signal at negligible cost.
* **Start-up calibration assumes the first 100 rows of a run are normal.** A run that starts faulty
  becomes the baseline. We would notice through an input check comparing burn-in statistics with
  their historical range (Week 7).
* **The alert budget is strict on this data, and recall at the budget is low** (5 of 7 on test,
  fewer than half on development). The operator must know that silence is not proof of health.

## What would change the decision

* An interval for (logistic - flow-rate) wholly above +0.05 on development data once at least 15
  more labelled faults exist.
* A fault family in operation that flow rate does not register. That would trigger a re-evaluation
  of Mahalanobis on that family.
* A change in the alert budget. A looser budget moves every operating point; this table would be
  rerun before any decision changes.
