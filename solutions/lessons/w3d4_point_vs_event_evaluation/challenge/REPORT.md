# Alert-budget report (Part A) - reference

Budget: at most 1 false alarm per 8 h of normal operation (0.125 per hour). Detector: |z| of flow
rate against each experiment's first 100 rows. Grid: 40 thresholds (dev score quantiles 0.50-0.999)
x min_duration {1, 3, 5, 10, 20, 30, 60} x merge_gap {0, 5, 10, 30, 60}. Run 2026-11-22.

## Chosen setting (from development experiments only)

threshold = 5.70, min_duration = 60, merge_gap = 5; feasible on dev: True.

## Results

| data | events found | false alarms | normal hours | rate per hour | 95 % upper bound | median delay |
|---|---|---|---|---|---|---|
| dev (selection data) | 12/25 | 0 | 4.59 | 0.00 | 0.65 | missed (detected only: 73-194 s) |
| test (frozen setting) | 4/9 | 0 | 1.63 | 0.00 | 1.84 | missed (detected only: 66-226 s) |
| fault-free recording | no events | 4 | 2.74 | 1.46 | 3.34 | - |

## What I would tell the engineer

"With the alarm tuned to raise no false alarms on our development recordings, it found 4 of 9
held-out faults, about one to four minutes after onset, and raised no false alarm in 1.6 hours of
held-out normal operation. That is far too little normal operation to show the one-per-eight-hours
budget is met: the data are compatible with up to 1.8 false alarms per hour, and on a separate
2.7-hour fault-free recording the same setting raised 4."

## What it would take to make the stronger claim

* Exposure: 24 hours of normal operation with zero false alarms gives a 95 % bound of 0.125 per hour;
  38 hours if one false alarm is observed. All SKAB normal time together (dev + test + fault-free)
  is about 9 hours, so the benchmark cannot certify this budget for any detector.
* The fault-free recording contradicts the dev estimate (4 false alarms in 2.74 h against 0 in 4.59 h).
  Its operating regime differs from the labelled experiments, so the false-alarm rate is not one
  number: it depends on the regime, which is exactly what the constant-rate assumption behind the
  bound ignores. The bound is optimistic when regimes vary.
* Half of the faults are missed at this setting, and the selection was made on 25 events. The dev
  figures (12/25, 0 false alarms) are optimistic by construction: this setting was the best of 1,400.

Things that are *not* acceptable in this report: "0.00 false alarms per hour, budget met";
a median delay quoted over the detected events only without saying so; tuning anything on the test
experiments after seeing this table.
