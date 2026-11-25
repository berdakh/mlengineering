# Baseline table for `flowguard` (fill in during lab task 5)

Data: SKAB v0.9 at the commit pinned in `project/get_skab.py`. Split: `make_splits(tidy, seed=0)`.
Evaluated rows: `t >= 100`. Threshold: best F1 on dev experiments, frozen for test.
Intervals are deliberately absent; they are added in w3d5. Until then no ordering between
nearby rows is claimed.

## Table

Paste the output of `python labs/w2d6_baselines_metrics/lab/baseline_table.py` here.

## What the floor is

Constant-score PR-AUC on test (equals prevalence):
What a clock achieves, and why:

## Reading the table (3-6 sentences each)

1. Which single comparison in the table changes what you will do next week, and why?
2. Global reference versus per-experiment burn-in: what does the difference tell you about the data?
3. The supervised row: which assumption does it rely on that the semi-supervised rows do not?
4. Which family is hardest, and is the difference large relative to nine test experiments?

## Decision

The baseline every later model has to beat, the metric it is judged on, and the threshold rule:
