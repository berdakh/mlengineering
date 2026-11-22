# Independent challenge: how many experiments would it take?

No walkthrough. Hints are in [`../hints/`](../hints/); try without them first.

## Situation

Your team lead reads the table from the lab and asks: "The supervised model is ahead of the
flow-rate z-score. How many more test experiments would we need to record before we could say so?"
Answer with a simulation, then write what can and cannot be claimed today.

`per_cluster_pr_auc.csv` in this directory holds the point-level PR-AUC of three detectors on each
of the 30 independent clusters of SKAB (REAL results from the reference lab run, v2 split, rows with
`t >= 100`; `logreg` scores for `dev` clusters are out-of-fold). Columns: `cluster, flow_z,
mahalanobis, logreg, side`.

## Task

1. In `power.py` implement

   * `power(draw, n_experiments, n_sim=500, seed=0, alpha=0.05, n_perm=499) -> float`
   * `required_experiments(draw, candidates, target_power=0.8, ...) -> int | None`

   `draw(rng, n)` returns `n` per-experiment differences; two factories are given
   (`normal_draw`, `empirical_draw`).

   The test whose power you estimate is fixed, so that results are comparable: a **two-sided
   sign-flip permutation test on the mean difference**, with `n_perm` random sign patterns and
   p-value `(1 + #{|permuted mean| >= |observed mean|}) / (1 + n_perm)`; a study "detects" the
   difference when `p <= alpha`.

2. Use it on the real differences (`empirical_draw` on `logreg - flow_z`, and on
   `mahalanobis - flow_z`) to fill the table in `CLAIMS.md`: power with the clusters you have, and the
   number of clusters needed for 80% power.

3. Write the claims paragraph and the assumptions in `CLAIMS.md`.

## Acceptance criteria

Automated (`python wb.py check w3d5 --challenge`):

* With no true difference, the rejection rate is close to `alpha` (the procedure is a valid test).
* Power agrees with the known answer for normally distributed differences.
* Power grows with the number of experiments and with the size of the difference.
* `required_experiments` returns the smallest sufficient candidate, or `None`.
* Results are reproducible from the seed. The whole suite runs in well under a minute.

By rubric (`solutions/.../assessment_answers.md`, after you have written yours):

* The claims paragraph distinguishes "no evidence of a difference" from "evidence of no difference".
* It states the unit of analysis and at least two assumptions of the power calculation.
* It gives a decision, not only a statistic.

## Optional extension (up to 1 hour)

* Replace the percentile interval in the lab with BCa via `scipy.stats.bootstrap` on per-cluster
  values and compare the limits for 7 and for 30 clusters.
* Repeat the power analysis for the **event recall** of two detectors (paired binary outcomes per
  event; the matching test is McNemar's exact test) and compare the required numbers.
