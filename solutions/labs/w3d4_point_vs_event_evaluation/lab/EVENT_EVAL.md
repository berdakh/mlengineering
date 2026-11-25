# Point-level versus event-level results for `flowguard` - reference reading

Data: SKAB v0.9 at commit `b2c0d46`. Split: manifest v2 repaired and frozen in w3d1
(`lab/splits/v2.json`; 27 dev, 7 test experiments: `other/1`, `other/14`, `valve1/5`, `valve1/8`,
`valve1/10`, `valve1/13`, `valve2/0`). Evaluated rows: `t >= 100` (6,659 test rows, 2,487 anomalous,
7 events, 1.22 h of normal operation). Threshold: best point F1 on dev, frozen. Run 2026-11-22.
No intervals (w3d5). Seven events: one event is 14 percentage points of recall.

## 1. Tables

Raw alarms (`min_duration=1, merge_gap=0`):

| detector | point P | point R | point F1 | F1 after point-adjust | events found | alarms | false alarms | redundant | event P | false alarms / h | median delay s | p90 delay s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| random | 0.373 | 1.000 | 0.544 | 0.544 | 1/7 | 9 | 8 | 0 | 0.111 | 6.6 | missed | missed |
| elapsed time t (no sensors) | 0.732 | 0.992 | 0.842 | 0.846 | 3/7 | 7 | 4 | 0 | 0.429 | 3.3 | missed | missed |
| flow_rate abs z, burn-in | 0.840 | 0.813 | 0.826 | 0.928 | 7/7 | 469 | 290 | 172 | 0.024 | 238.6 | 4 | 43 |
| max abs z, burn-in | 0.591 | 0.897 | 0.713 | 0.763 | 6/7 | 275 | 217 | 52 | 0.027 | 178.5 | 5 | missed |
| Mahalanobis, burn-in | 0.696 | 0.766 | 0.729 | 0.857 | 6/7 | 245 | 129 | 110 | 0.044 | 106.1 | 16 | missed |
| logistic regression (supervised) | 0.825 | 0.846 | 0.835 | 0.918 | 7/7 | 462 | 319 | 136 | 0.021 | 262.4 | 4 | 31 |

Post-processed (`min_duration=10, merge_gap=30`; delays include the 9 confirmation rows):

| detector | point F1 | events found | alarms | false alarms | redundant | event P | false alarms / h | median delay s | p90 delay s |
|---|---|---|---|---|---|---|---|---|---|
| random | 0.544 | 0/7 | 7 | 7 | 0 | 0.000 | 5.8 | missed | missed |
| elapsed time t (no sensors) | 0.842 | 3/7 | 7 | 4 | 0 | 0.429 | 3.3 | missed | missed |
| flow_rate abs z, burn-in | 0.826 | 3/7 | 17 | 14 | 0 | 0.176 | 11.5 | missed | missed |
| max abs z, burn-in | 0.713 | 3/7 | 17 | 14 | 0 | 0.176 | 11.5 | missed | missed |
| Mahalanobis, burn-in | 0.729 | 5/7 | 11 | 5 | 1 | 0.500 | 4.1 | 52 | missed |
| logistic regression (supervised) | 0.835 | 2/7 | 17 | 15 | 0 | 0.118 | 12.3 | missed | missed |

(The post-processing values were picked for illustration, not tuned. Tuning them is the challenge.)

## 2. Where the metrics disagree

* **Random / flag-everything.** The best-F1 dev threshold for a random score flags almost every row:
  point F1 0.544, recall 1.000. At event level it is a handful of long alarms, almost all false:
  1/7 events found raw, 0/7 post-processed.
* **The clock wins point F1.** Elapsed time, with no sensor input, has the highest point F1 in the
  table (0.842) and finds 3/7 events. Point F1 ranks a protocol leak first; the event columns put it
  last among the non-random rows (section 3).
* **Supervised logistic regression versus the single-sensor z-score.** Point F1 0.835 against 0.826;
  both find 7/7 raw with median delay 4 s. They are indistinguishable at this test size.
* **Raw alarm streams are unusable.** 469 alarms for 7 faults from the single sensor, 239 false alarms
  per hour. Point precision 0.840 gave no hint: the false flags are few rows but many separate alarms.
* **Post-processing reverses the ranking.** With `min_duration=10, merge_gap=30` at the same
  thresholds, Mahalanobis (point F1 0.729, worst of the sensor detectors) is best: 5/7 events, 5 false
  alarms, median delay 52 s; the single sensor and logistic regression drop to 3/7 and 2/7 because
  their merged alarms start before the onset.
* **Point-adjust** lifts the single-sensor F1 from 0.826 to 0.928 for the same flags without any
  change to the detector.

## 3. The clock

Threshold `t >= 570`. Under the lab's rule it detects 3/7 (`valve1/13`, `valve2/0`, `other/1`) with
delays of 0, 9 and 14 s, and its four other alarms are false alarms that began 1-7 rows *before* the
labelled onset (`valve1/5`, `valve1/8`, `valve1/10`, `other/14`). With an early tolerance of 5 rows
it detects 6/7; under any-overlap it detects 7/7 with no false alarm. A detector with no sensor input
"finds" every fault within seconds because the experiments were scripted to start the fault near row
570: every test onset lies between rows 557 and 577. Event recall and delay are as exposed to this
protocol leak as point F1 was. Event metrics do not protect against leakage. Held-out conditions do.

## 4. Post-processing

`min_duration=10, merge_gap=30` cuts the single-sensor detector from 469 alarms to 17 and from
238.6 to 11.5 false alarms per hour, but at the best-F1 threshold (2.40) it loses four events (7/7 to
3/7): isolated bursts before the onset merge into an alarm that starts in normal operation. For
Mahalanobis it works as intended: 245 alarms to 11, 106.1 to 4.1 false alarms per hour, 6/7 to 5/7
events. (Why the two detectors respond so differently was not investigated.) The threshold and the post-processing
parameters interact, so they are tuned together, on dev experiments only (the challenge).

## 5. What cannot be claimed

* Any false-alarm rate that matters operationally. Zero false alarms in the 1.22 test hours would
  still allow up to 2.46 per hour at 95 % confidence; a budget of one per 8 hours needs 24 hours of
  normal operation with none.
* Any ranking of the top detectors: they differ by one or two events out of seven.
* Any delay percentile beyond the median: p90 of seven values is the worst case.
* Hours depend on the convention: 1.22 h wall clock (the same with gaps capped at 5 s: the seven
  test experiments have no gap longer than 5 s), 1.16 h if one wrongly counts rows.

## 6. Decision

Report, per protocol: events found (count and denominator), false alarms and hours of normal
operation (counts, then the rate), median delay with missed events counted as infinite, each with
the w3d5 intervals; point PR-AUC stays as a secondary ranking metric. Matching rule: an alarm
detects an event when it starts inside it (early tolerance 0 rows by default, stated whenever
changed); repeats are redundant; alarms raised in normal operation are false alarms even if they
run into an event. Point-adjusted scores are never reported.
