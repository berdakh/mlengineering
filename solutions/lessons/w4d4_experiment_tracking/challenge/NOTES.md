# Reference notes for the w4d4 challenge (real SKAB registry, 2026-11-22)

```text
$ python lessons/w4d4_experiment_tracking/challenge/compare_groups.py --runs-dir runs \
      --a detector.n_estimators=200 --b detector.n_estimators=50 --metric dev_pooled_pr_auc
A = {'detector.n_estimators': 200}  vs  B = {'detector.n_estimators': 50}  on dev_pooled_pr_auc
| pair | A | B | A - B |
|---|---|---|---|
| 0 | 0.6401 | 0.6453 | -0.0051 |
| 1 | 0.6575 | 0.6317 | +0.0258 |
| 2 | 0.6457 | 0.6272 | +0.0185 |
mean difference +0.0131 (sd 0.0162, 3 pairs; A better in 2)
```

(The command was run with the reference solution copied into the challenge folder.)

**What the seed controls here.** In scikit-learn 1.9.1, an `IsolationForest` with `random_state = s`
draws the per-tree seeds from one generator, so the 200-tree forest contains the 50-tree forest's trees
as its first 50 (checked: 50 of 50 trees identical on a small synthetic input). The pair (200, s) - (50, s)
therefore isolates the effect of the 150 extra trees, which makes pairing meaningful.

**What it shows.** With 3 pairs, a mean difference of +0.013 and an sd of 0.016, the extra trees helped in
2 of 3 seeds; that is no evidence either way (a sign test on 3 pairs cannot reach p < 0.25). It also
compares development scores of an unselected detector that is about 0.09 below Mahalanobis, so even a
real gain would not change the project's decision. A useful statement: "more trees did not change the
picture; isolation forest stays below Mahalanobis on development data".
