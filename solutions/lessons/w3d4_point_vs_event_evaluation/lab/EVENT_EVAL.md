# Point-level versus event-level results for `flowguard` - reference reading

Data: SKAB v0.9 at commit `b2c0d46`. Split: manifest v2, seed 0, overlap groups kept together
(25 dev, 9 test experiments: `other/2`, `other/3`, `other/4`, `other/6`, `valve1/3`, `valve1/10`,
`valve1/12`, `valve1/14`, `valve2/3`). Evaluated rows: `t >= 100` (8,923 test rows, 3,577 anomalous,
9 events, 1.63 h of normal operation). Threshold: best point F1 on dev, frozen. Run 2026-11-22.
No intervals (w3d5). Nine events: one event is 11 percentage points of recall.

## 1. Tables

Raw alarms (`min_duration=1, merge_gap=0`):

| detector | point P | point R | point F1 | F1 after point-adjust | events found | alarms | false alarms | redundant | event P | false alarms / h | median delay s | p90 delay s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| random | 0.401 | 1.000 | 0.572 | 0.572 | 0/9 | 10 | 10 | 0 | 0.000 | 6.1 | missed | missed |
| elapsed time t (no sensors) | 0.679 | 0.889 | 0.770 | 0.772 | 4/9 | 9 | 5 | 0 | 0.444 | 3.1 | missed | missed |
| flow_rate abs z, burn-in | 0.889 | 0.703 | 0.785 | 0.958 | 9/9 | 403 | 156 | 238 | 0.055 | 95.8 | 34 | 58 |
| max abs z, burn-in | 0.715 | 0.458 | 0.558 | 0.793 | 7/9 | 221 | 98 | 116 | 0.067 | 60.2 | 60 | missed |
| Mahalanobis, burn-in | 0.721 | 0.509 | 0.596 | 0.851 | 8/9 | 238 | 127 | 103 | 0.059 | 78.0 | 60 | missed |
| logistic regression (supervised) | 0.906 | 0.744 | 0.817 | 0.963 | 8/9 | 387 | 144 | 235 | 0.053 | 88.4 | 43 | missed |

Post-processed (`min_duration=10, merge_gap=30`; delays include the 9 confirmation rows):

| detector | point F1 | events found | alarms | false alarms | redundant | event P | false alarms / h | median delay s | p90 delay s |
|---|---|---|---|---|---|---|---|---|---|
| random | 0.572 | 0/9 | 9 | 9 | 0 | 0.000 | 5.5 | missed | missed |
| elapsed time t (no sensors) | 0.770 | 4/9 | 9 | 5 | 0 | 0.444 | 3.1 | missed | missed |
| flow_rate abs z, burn-in | 0.785 | 8/9 | 15 | 7 | 0 | 0.533 | 4.3 | 52 | missed |
| max abs z, burn-in | 0.558 | 5/9 | 13 | 7 | 1 | 0.417 | 4.3 | 425 | missed |
| Mahalanobis, burn-in | 0.596 | 5/9 | 17 | 11 | 1 | 0.312 | 6.8 | 424 | missed |
| logistic regression (supervised) | 0.817 | 7/9 | 18 | 9 | 2 | 0.438 | 5.5 | 62 | missed |

(The post-processing values were picked for illustration, not tuned. Tuning them is the challenge.)

## 2. Where the metrics disagree

* **Random / flag-everything.** The best-F1 dev threshold for a random score flags every row: point
  F1 0.572, recall 1.000. At event level it is one alarm per experiment that is on from the first
  evaluated row: 0/9 events, every alarm a false alarm.
* **Supervised logistic regression versus the single-sensor z-score.** Logistic regression leads on
  point F1 (0.817 against 0.785). At event level the single sensor is at least as good: 9/9 against
  8/9 raw, 8/9 against 7/9 post-processed, with a shorter median delay (34 s against 43 s raw).
  With nine events neither ordering is established; the point is that point F1 did not predict it.
* **Raw alarm streams are unusable.** 403 alarms for 9 faults, 96 false alarms per hour. Point
  precision 0.889 gave no hint: the false flags are few rows but many separate alarms.
* **Point-adjust** lifts F1 from 0.785 to 0.958 for the same flags without any change to the detector.

## 3. The clock

Threshold `t >= 571`. Under the lab's rule it detects 4/9 with delays of 1, 2, 3 and 8 s, and its
five other alarms are false alarms: three began 2 rows *before* the labelled onset, one began 225
rows before it (`other/4`), one after the fault was over (`other/2`). With an early tolerance of 5 rows it detects 7/9; under any-overlap it detects 8/9
with one false alarm. A detector with no sensor input "finds" most faults within seconds because
the experiments were scripted to start the fault near row 570. Event recall and delay are as
exposed to this protocol leak as point F1 was; only `other/2` (onset at row 104) and `other/4`
(onset at row 796) break it. Event metrics do not protect against leakage. Held-out conditions do.

## 4. Post-processing

`min_duration=10, merge_gap=30` cuts the single-sensor detector from 403 alarms to 15 and from
95.8 to 4.3 false alarms per hour. Cost: one event lost (9/9 to 8/9), median delay 34 s to 52 s
(9 s of that is the confirmation wait), and p90 becomes "missed". For the multivariate scorers the
merged alarm often starts before the onset, so it stops counting: 7/9 to 5/9 and a median delay
of about 420 s (the hit is a later alarm near the end of the fault). These parameters are part of
the detector. They are tuned on dev experiments only.

## 5. What cannot be claimed

* Any false-alarm rate that matters operationally. Zero false alarms in the 1.63 test hours would
  still allow up to 1.84 per hour at 95 % confidence; a budget of one per 8 hours needs 24 hours of
  normal operation with none.
* Any ranking of the top detectors: they differ by one event out of nine.
* Any delay percentile beyond the median: p90 of nine values is the worst or second-worst case.
* Hours depend on the convention: 1.63 h wall clock, 1.56 h with gaps capped at 5 s, 1.49 h if one
  wrongly counts rows. The largest contribution is the 247 s gap in `other/2`.

## 6. Decision

Report, per protocol: events found (count and denominator), false alarms and hours of normal
operation (counts, then the rate), median delay with missed events counted as infinite, each with
the w3d5 intervals; point PR-AUC stays as a secondary ranking metric. Matching rule: an alarm
detects an event when it starts inside it (early tolerance 0 rows by default, stated whenever
changed); repeats are redundant; alarms raised in normal operation are false alarms even if they
run into an event. Point-adjusted scores are never reported.
