# Streaming alarm rule: development report (w5d3 challenge, reference)

## Command and conditions

```text
python solutions/lessons/w5d3_online_inference/challenge/evaluate_hysteresis.py
```

27 development experiments of the frozen manifest `splits/v2.json`; model bundle `flowguard-z-1.0.0`
(threshold 7.2441, burn-in 100); the first 100 rows of each run are excluded from evaluation.
Delays are over detected events only, so medians of rows with different detection counts are not
directly comparable.

## Results (authoring run, 2026-11-22)

| Rule | Events detected | Alarm events | False alarms / h | Median delay (detected) |
|---|---|---|---|---|
| batch post-processing (min_duration 30, merge_gap 10) | 11/27 | 12 | 0.00 | 90 s |
| stream hysteresis k=1, m=1 (raw exceedances) | 11/27 | 179 | 2.20 | 60 s |
| stream hysteresis k=1, m=60 | 11/27 | 14 | 0.60 | 60 s |
| stream hysteresis k=5, m=10 | 10/27 | 11 | 0.20 | 65 s |
| stream hysteresis k=10, m=10 | 10/27 | 11 | 0.20 | 70 s |
| stream hysteresis k=30, m=10 | 9/27 | 9 | 0.00 | 91 s |

## Recommendation

Use **k = 30, m = 10** if the alert budget of 1 false alarm per 8 h (0.125/h) is binding: it is the only
streaming rule in the grid with no false alarms on development data, and it raises 9 alarm events for
9 detected faults. It detects two fewer faults than the batch rule (9 against 11) because the batch rule
merges exceedance runs separated by up to 10 rows *before* applying the 30-row minimum; a stream cannot
look back and merge, it needs 30 consecutive exceedances. k = 5 or 10 with m = 10 detects one more fault
and reacts about 20 s sooner but exceeds the budget (0.20/h), so it is the right choice only if the
budget can be renegotiated. m barely matters once k >= 5 (alarms that clear quickly rarely re-raise).
With 27 experiments and 9-11 detections, a difference of one or two events is within noise (w3d5): the
decision rests on the budget, not on the event counts.
