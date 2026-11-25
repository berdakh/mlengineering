# Baseline table for `flowguard` - reference reading

Data: SKAB v0.9 at commit `b2c0d46`. Split: `make_splits(tidy, seed=0)` (25 dev, 9 test experiments).
Evaluated rows: `t >= 100`. Threshold: best F1 on dev, frozen for test. Run 2026-11-21.
No intervals yet (w3d5): with nine test experiments, differences of a few hundredths are not claims.

## Table

| baseline | dev PR-AUC | test PR-AUC | test P | test R | test F1 | PR-AUC other | PR-AUC valve1 | PR-AUC valve2 |
|---|---|---|---|---|---|---|---|---|
| constant | 0.388 | 0.373 | 0.373 | 1.000 | 0.544 | 0.358 | 0.383 | 0.384 |
| random | 0.388 | 0.369 | 0.373 | 1.000 | 0.544 | 0.352 | 0.381 | 0.382 |
| elapsed time t (no sensors) | 0.501 | 0.513 | 0.722 | 0.990 | 0.835 | 0.567 | 0.484 | 0.485 |
| flow_rate abs z, global reference | 0.675 | 0.752 | 0.910 | 0.573 | 0.703 | 0.684 | 0.935 | 0.885 |
| max abs z, global reference | 0.786 | 0.747 | 0.909 | 0.573 | 0.703 | 0.617 | 0.935 | 0.880 |
| Mahalanobis, global reference | 0.664 | 0.580 | 0.374 | 1.000 | 0.544 | 0.679 | 0.706 | 0.613 |
| flow_rate abs z, burn-in | 0.788 | 0.805 | 0.732 | 0.765 | 0.748 | 0.721 | 0.925 | 0.726 |
| max abs z, burn-in | 0.697 | 0.745 | 0.571 | 0.921 | 0.705 | 0.807 | 0.732 | 0.656 |
| Mahalanobis, burn-in | 0.700 | 0.734 | 0.639 | 0.836 | 0.724 | 0.801 | 0.757 | 0.675 |
| logistic regression on burn-in abs z (supervised) | 0.829 | 0.827 | 0.752 | 0.816 | 0.783 | 0.751 | 0.934 | 0.816 |

Test prevalence of anomalous rows: 0.373.

## What the floor is

PR-AUC floor = prevalence = 0.373. F1 floor = 2π/(1+π) = 0.544 (flag everything).

A clock reaches test F1 0.835, the highest in the table, with threshold t >= 572. In 31 of 34
experiments the anomaly starts between t = 550 and t = 600. This is how the benchmark was recorded,
not a property of pumps. Its PR-AUC is only 0.513 because the anomaly ends before the recording does,
so the highest-ranked rows (latest times) are normal.

## Reading the table

1. **The comparison that changes next week's work** is clock versus everything else. F1 at a tuned
   threshold can be won without sensors, so (a) F1 is not the project's headline metric, (b) any
   feature that encodes elapsed time or slow warm-up drift is a leakage suspect to be tested in w3d1,
   (c) event-level metrics with detection delay (w3d4) are needed, since a clock cannot detect an
   onset it was not told about.
2. **Global reference versus burn-in.** The fault-free recording was taken in a different operating
   regime (flow about 125 L/min, standard deviation 1.6; labelled experiments' normal rows average
   about 63 with standard deviation about 42). Scores against it mostly measure "how far is this
   experiment's regime from the reference". For Mahalanobis the dev threshold flags every test row.
   Burn-in removes the between-experiment offset, the analogue of per-subject normalisation.
   The global `flow_rate`/max-abs-z rows still rank well on the valve families, which looks like a
   regime coincidence and should not be relied on.
3. **Supervised row.** Best PR-AUC (0.827), by a margin that is not established without intervals.
   It assumes future faults resemble labelled ones. Its weakest family is `other` (0.751), the family
   with heterogeneous fault mechanisms; protocol B (hold out `other` entirely) is the proper test.
4. **Families.** `valve1` is nearly solved by one sensor (0.925-0.935). `other` and `valve2` are
   harder for flow alone; multivariate burn-in scorers do better on `other` (0.80) and worse on the
   valves. `valve2` has one test experiment: its column is an anecdote.

Also visible: one sensor beats eight under burn-in on the pooled metric. Max-over-sensors adds the
false alarms of seven mostly uninformative sensors.

## Decision

Bar to beat: **`flow_rate` abs z with 100-row burn-in** (test PR-AUC 0.805), semi-supervised, no fault
labels needed. Reference point: supervised logistic regression (0.827). Headline metric for now:
PR-AUC with the 0.373 floor printed beside it; per-family breakdown always shown; F1 only at a
dev-frozen threshold and never without the clock row. To be replaced by event-level metrics in w3d4.
