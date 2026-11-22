# Error analysis: `flow_rate` burn-in z-score on SKAB development experiments

Fill this in from the output of `python lessons/w3d6_error_analysis_transfer/lab/error_report.py`.
One page. Numbers come from your run; do not copy them from the lesson text.

## Object

| | |
|---|---|
| Model | |
| Threshold and how it was chosen | |
| Data (split version, which side, rows excluded) | |
| Date / commit | |

## Headline

Metric, its mean over experiments, and its spread (min, max). Row-pooled figure if it differs.

## Failure modes, ranked

| Rank | Kind | Size (segments / rows / experiments) | Evidence | Suspected cause | Cost (who is hurt, how) | Fixability (0-1) and why |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

## Slices checked and found unremarkable

List every slice you looked at that showed no supportable difference, with its size.

## Label issues

What is known about label noise in these experiments, and the ceiling it implies.

## Next experiments (one per top failure mode)

For each: the change, the metric expected to move and in which direction, the side effect you
expect, and the result that would mean the hypothesis is wrong.

## Limits

What was not examined. Which statements rest on fewer than five experiments. What would change the ranking.
