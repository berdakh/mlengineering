# SKAB sweep notes (reference)

## Commands run

`flowguard sweep` with `sweeps/mahalanobis.toml` (6 runs, about 3 s) and `sweeps/iforest.toml` (6 runs,
about 17 s); a second invocation of each reported `"skipped": 6`.

## Results table (dev_pooled_pr_auc, 27 development experiments, rows t >= 200)

| sweep | burn_in | kind | n_estimators | shrinkage | n | mean | sd |
|---|---|---|---|---|---|---|---|
| iforest | 200 | iforest | 50 | - | 3 | 0.6347 | 0.0094 |
| iforest | 200 | iforest | 200 | - | 3 | 0.6478 | 0.0089 |
| mahalanobis | 100 | mahalanobis | - | 0.0 | 1 | 0.7050 | nan |
| mahalanobis | 100 | mahalanobis | - | 0.1 | 1 | 0.7071 | nan |
| mahalanobis | 100 | mahalanobis | - | 0.3 | 1 | 0.7096 | nan |
| mahalanobis | 200 | mahalanobis | - | 0.0 | 1 | 0.7301 | nan |
| mahalanobis | 200 | mahalanobis | - | 0.1 | 1 | 0.7321 | nan |
| mahalanobis | 200 | mahalanobis | - | 0.3 | 1 | 0.7349 | nan |

## Reproduction

* run id: `0668c9c60359` (isolation forest, 200 trees, seed 2)
* `match: true`, `max_abs_diff: 0.0` (about 5 s)

## Next sweep

Burn-in length is the only parameter that moved Mahalanobis noticeably, so sweep it further (150, 250,
300, keeping the scored rows fixed at t >= 300) before touching shrinkage. Any finer shrinkage grid is
noise-chasing: its whole range covers 0.005.
