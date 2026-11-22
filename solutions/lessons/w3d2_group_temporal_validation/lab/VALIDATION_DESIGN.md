# Validation design memo: `flowguard` (reference)

Manifest: `splits/v2.json` (repaired in w3d1: 7 test, 27 development experiments). Numbers from
`compare_schemes.py`, 2026-11-22, development experiments only.

## 1. Deployment question

> The detector will run on recordings from pumps and runs it has never seen, of the fault families it
> was developed on, and must flag abnormal operation as it happens; whether it transfers to a fault
> mechanism it has never seen is a separate, secondary question.

## 2. Estimand

Expected PR-AUC (and, from w3d4, event-level metrics) of the training procedure applied to the
development experiments, on **whole experiments not used in training**, drawn from the same families.
Secondary: the same on a family absent from training.

## 3. Primary scheme and why

* **Primary: scheme 4, experiments held out, using the manifest's four frozen folds.** The unit that is
  new in deployment is the experiment, so whole experiments are withheld; overlap groups stay inside one
  fold; folds are frozen so that every model comparison is paired.
* **Rejected: scheme 1 (rows shuffled)** answers "new rows of recordings already seen", which never
  happens. **Schemes 2-3 (time blocks within experiments)** answer "another stretch of a recording
  already seen"; also not the deployment situation, and with an anomaly that starts near row 570 the
  blocks have very different class balance.
* **Stress tests kept: scheme 5 (one family held out)** for the secondary question; **scheme 6 (forward
  by recording day)** only as a sanity check, because day and family are confounded and it has two
  folds.

## 4. What the table does and does not support

| Claim | Supported by | Not supported because |
|---|---|---|
| A row split flatters the raw-sensor forest by about 0.17 ROC-AUC | scheme 1 0.985 vs scheme 4 0.818 | - |
| The burn-in-normalised regression depends much less on recognising experiments | its 1-vs-4 gap is 0.05 (0.867 vs 0.814) | it is not shown that it is *better*: on scheme 4 the two models are within 0.004 ROC-AUC, far inside the fold spread (forest folds 0.63-0.94) |
| Performance drops for an unseen family | scheme 5: `other` held out gives 0.529 (forest) and 0.653 (regression) | `other` is also a different recording day and a mixture of 14 different fault types; the drop cannot be attributed to "new mechanism" alone |
| The regression transfers to a later day | scheme 6, second fold 0.789 | two folds; first fold validates on one overlap group (three copies of one recording) |
| Pooled numbers can be compared across schemes as a ranking of schemes | - | each scheme estimates a different quantity; also pooled ROC-AUC mixes scores from differently trained models (scheme 3 regression: pooled 0.704 below every fold) |

Why the forest loses more: on raw sensor values each experiment has its own operating point, so rows
identify their experiment and a flexible model memorises "this experiment's normal level". Burn-in
z-scores remove each experiment's offset, so there is less to memorise.

Why pooled can be below every fold: each fold's model is fitted to a different training set with a
different class balance (block 0 is nearly all normal, blocks 2-3 mostly anomalous), so the scores of
different folds are on different scales. Pooling ranks them against each other. Per-fold values, or
pooling only after calibration, are the right summaries; this is a property of the pooling, not of the
detector.

## 5. Buffer

Rolling-mean window w = 30 rows, label horizon h = 0, so buffer = 29 rows on each side of a validation
block. It applies only to within-experiment time blocks (scheme 3). Between held-out experiments no
samples are shared (overlap groups are kept together), so no buffer is needed for the primary scheme.

## 6. Known weaknesses

1. 27 development experiments in four folds; a 0.02 difference between models is not resolvable (w3d5
   will quantify it).
2. Family, recording day and fault type are confounded; no scheme separates them with this data.
3. The test set has 7 experiments (2 of `other`); conclusions about `other` rest on two recordings.
4. Protocol leakage (onset near row 570) is untouched by any split; features must exclude time (w3d1).
