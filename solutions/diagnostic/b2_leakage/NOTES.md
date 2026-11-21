# b2_leakage - reviewer notes

Reference: `lab/fixed_eval.py`. Verified with `python tools/verify_checks.py diagnostic/b2_leakage`.

## The planted problems in `leaky_eval.py`

| # | Problem | Kind | Measured effect on AP (this simulation) |
|---|---|---|---|
| 1 | `retention_offer_sent` used as a feature | target leakage: written after the customer asks to cancel | large - see table below |
| 2 | `last_invoice_offset_days` used as a feature | target leakage through the future: computed from the *full* invoice history; 0 for every churner | large |
| 3 | Stratified random row split | validation does not match deployment: training rows come from the same and later months than test rows; the September price increase is in both | **not measurable here** with honest features |
| 4 | Dummies, median imputation and scaling fitted on all rows | train-test contamination in preprocessing | **not measurable here** (0.210 vs 0.209) |

Executed results (logistic regression; AP; test prevalence 0.074 random / 0.089 temporal):

| Evaluation | AP |
|---|---|
| `leaky_eval.py` as shipped | 0.955 |
| temporal split, honest features + `retention_offer_sent` | 0.694 |
| temporal split, honest features + `last_invoice_offset_days` | 0.463 |
| random split, honest features + `last_invoice_offset_days` | 0.858 |
| **reference: temporal split, honest features, pipeline** | **0.209** |
| random row split, honest features (20 seeds) | 0.191 +/- 0.022 |
| customer-grouped random split, honest features (20 seeds) | 0.196 +/- 0.021 |
| temporal split, honest features, preprocessing fitted on all rows | 0.210 |

What this shows, and what a strong submission says:

* Almost the entire inflation (0.96 vs 0.21) comes from the two leaky **columns**. Finding only the
  obvious one still leaves a score more than twice the honest one.
* The random split and the all-rows preprocessing are still wrong, but **on this data they do not
  inflate the score measurably**. A strong `FINDINGS.md` reports that honestly ("fixed by construction;
  effect not detectable here") instead of asserting that every leak inflates results. Leakage is fixed
  because the procedure is invalid, not because a number moved.
* The split choice follows from the deployment question (score future months), not from a reflex.
  A customer-grouped split would answer "how well do we rank customers we have never seen?", which is
  not the question here: almost all customers scored next month are already in the training data.
  Insisting on a subject-wise split by habit is the specific transfer error this section looks for.
  (A combined design - temporal split, reported separately for new vs. existing customers - is a
  good extension answer.)
* The random split interacts with leak #2: the offset column is far more damaging under a random
  split (0.858) than a temporal one (0.463), because its meaning changes with the distance to the end
  of the data.

## What the corrected number still does not establish

Uncertainty (one split, 175 test positives); stability under the price change; whether features are
truly point-in-time in the source systems (the snapshot table was built by someone else); calibration;
whether acting on the ranking changes outcomes.

## Common incorrect answers and why they fail

* Drops `retention_offer_sent` only (mutant `kept_subtle_leak`) - the column description ("last
  invoice in the billing system") has to be read with the question "known when?".
* Keeps the random split because "it is stratified" (mutant `random_split`).
* Switches to `GroupShuffleSplit`/`GroupKFold` by customer (mutant `group_split_only`).
* Moves the scaler into a pipeline but leaves `get_dummies`/`fillna(median)` on the full frame
  (mutant `preprocessing_outside_model`).
* Removes legitimately available features out of caution (e.g. `failed_payments_90d`) - costs signal;
  not leakage, since it is computed from the 90 days *before* the snapshot.
* Declares every problem "inflates the score" without measuring.
* Uses `snapshot_date` month as a raw feature - cannot generalise to unseen months; mention in review.

## Rubric

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Target leakage | Both columns found with the mechanism ("known only after the outcome") | Obvious one found; subtle one only via the check's upper bound | Neither |
| Validation design | Temporal split derived from the deployment question; can say why grouped-only is not the answer here | Temporal split chosen without justification, or grouped split defended | Random split kept |
| Preprocessing leakage | All fitted steps inside the estimator; mechanism explained | Fixed for the scaler only | Not noticed |
| Scientific honesty | Separates measured effects from expected ones; states remaining limits | Effects asserted, not measured | Reports only the new number |
