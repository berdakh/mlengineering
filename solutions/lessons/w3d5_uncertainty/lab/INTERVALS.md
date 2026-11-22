# Baselines with intervals - reference reading

Run 2026-11-22. SKAB v0.9 at commit `b2c0d46`; split: the v2 manifest repaired and frozen in w3d1
(`lab/splits/v2.json`, 7 test and 27 development experiments, overlap groups kept together);
evaluated rows `t >= 100`; 2,000 cluster resamples, seed 0.

## Tables

```
split v2: 7 test experiments = 7 independent clusters; 34 labelled experiments = 30 clusters; n_boot = 2000

A. Test set, pooled point-level PR-AUC, 95% intervals
| baseline | cluster bootstrap (correct unit) | row bootstrap (wrong unit) | width ratio |
|---|---|---|---|
| elapsed time t (no sensors) | 0.524 [0.484, 0.588] | [0.507, 0.540] | 3.1x |
| flow_rate abs z, burn-in | 0.884 [0.811, 0.928] | [0.872, 0.895] | 5.0x |
| Mahalanobis, burn-in | 0.759 [0.611, 0.869] | [0.740, 0.776] | 7.2x |
| logistic regression (supervised) | 0.900 [0.852, 0.938] | [0.889, 0.913] | 3.6x |

B. All labelled experiments (valid only for scorers that were never fitted to labels)
| baseline | pooled PR-AUC | mean per-cluster PR-AUC |
|---|---|---|
| elapsed time t (no sensors) | 0.503 [0.485, 0.526] | 0.524 [0.488, 0.569] |
| flow_rate abs z, burn-in | 0.789 [0.716, 0.857] | 0.812 [0.751, 0.864] |
| Mahalanobis, burn-in | 0.703 [0.615, 0.784] | 0.728 [0.649, 0.806] |

C. Paired comparisons (difference in pooled PR-AUC, A minus B)
| A | B | data | clusters | difference [95% CI] | A better in | sign test p | permutation p |
|---|---|---|---|---|---|---|---|
| logistic regression (supervised) | flow_rate abs z, burn-in | test | 7 | +0.016 [-0.003, +0.049] | 6/7 | 0.1250 | 0.0781 |
| Mahalanobis, burn-in | flow_rate abs z, burn-in | test | 7 | -0.125 [-0.278, -0.013] | 2/7 | 0.4531 | 0.1875 |
| Mahalanobis, burn-in | flow_rate abs z, burn-in | all labelled | 30 | -0.086 [-0.212, +0.029] | 12/30 | 0.3616 | 0.1202 |
| flow_rate abs z, burn-in | elapsed time t (no sensors) | all labelled | 30 | +0.286 [+0.217, +0.349] | 27/30 | 0.0000 | 0.0001 |

D. Event-level sanity count on the test set (threshold = best F1 on dev; an event counts as
   detected if at least one of its rows is flagged; false alarms are NOT counted, see w3d4)
| baseline | events detected | Wilson 95% interval |
|---|---|---|
| flow_rate abs z, burn-in | 7/7 | [0.65, 1.00] |
| logistic regression (supervised) | 7/7 | [0.65, 1.00] |
```

## 1. Unit of resampling

One cluster is one *independent recording session*: an overlap group of SKAB files that share
identical rows (`other/2+3+4`, `other/10+11`, `other/12+13`) or, for every other file, the experiment
itself. Not the row, because rows of an experiment share its operating conditions and move together
(row-level intervals above are 3 to 7 times narrower). Not always the experiment, because files
that contain the same rows are not independent draws. The labelled data therefore have 30 clusters.
The frozen test set has 7, one per experiment: w3d1 moved every overlap group to development.

## 2. What each interval covers, and what it does not

Covers: how much each number would move with a different draw of clusters *from the same testbed
and protocol*, for the fixed scorers and thresholds.

Does not cover: refitting the logistic regression on other development experiments; seed noise (none
of these scorers is stochastic); the choice of burn-in length, features and split seed; any
difference between this testbed and a real plant; the label-timing regularity (anomalies start at
row 550-600 in 31 of 34 files). With 7 clusters the percentile intervals also undercover: in the
worked example a nominal 95% interval contained the truth about 87% of the time.

## 3. Claims

* Supervised logistic regression versus flow-rate z-score (test, 7 clusters): **cannot claim a
  difference.** +0.016 PR-AUC, interval [-0.003, +0.049], better on 6 of 7 clusters, sign test
  p = 0.125, permutation p = 0.078. Nor can we claim they are equal: the interval admits an
  advantage of up to 0.05.
* Mahalanobis versus flow-rate z-score: **cannot claim a difference.** On the 7 test clusters the
  percentile interval, -0.125 [-0.278, -0.013], excludes zero, but the sign test (p = 0.45) and the
  permutation test (p = 0.19) do not reject, and a 7-cluster percentile interval undercovers; on all
  30 clusters the estimate favours flow rate by 0.086 with interval [-0.212, +0.029], p = 0.12.
  Their per-cluster scores are almost uncorrelated (-0.12), so they fail on different experiments.
* Flow-rate z-score versus elapsed time (30 clusters): **can claim** that the sensor carries
  information beyond the recording protocol: +0.286 [+0.217, +0.349], better on 27 of 30.
* Event detection, 7 of 7 at the development threshold: compatible with a true rate as low as 65%;
  no statement about false alarms.

## 4. What would change my mind

More independent experiments, above all in the `other` family, where per-cluster scores (all three detectors) range from
0.41 to 1.00. More rows per experiment would not help. Before collecting anything: event-level
metrics with false alarms (w3d4), since point-level PR-AUC rewards flagging long segments; and
protocol B (hold out `other`), which changes the question from "these experiments" to "unseen fault
mechanisms". Given that the supervised and unsupervised baselines are indistinguishable, the choice
between them should be made on what they need (fault labels or not), not on this table.
