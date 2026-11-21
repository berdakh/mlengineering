# Hint 2 - approach

**Lab, metrics.**

1. Sort by score descending. Compute cumulative positives `tp` and row counts.
2. Keep only the positions where the score changes (the last row of each tie group) plus the final row.
3. At those positions: `fp = count - tp`, `precision = tp / count`, `recall = tp / n_pos`.
4. Average precision: sum of `(recall_k - recall_{k-1}) * precision_k`, with `recall_0 = 0`.
5. Best F1: `2*tp / (2*tp + fp + fn)` at the same positions; the threshold is the score at the argmax.
   Flagging is `>=`, so the threshold *is* an observed score.

**Lab, scorers.**

1. Store `mean_` and `std_` in `fit`; replace zero standard deviations by 1.
2. `MaxAbsZScorer.score`: `abs(z).max(axis=1)`.
3. Mahalanobis: work on z-scores (unit-free). Correlation matrix of the training z-scores, blended
   with the identity (`(1-a)*R + a*I`, a around 0.1), inverted once in `fit`. In `score`:
   `sqrt(sum_jk z_j P_jk z_k)` per row.

**Lab, benchmark.** Build boolean masks: `usable = t >= burn_in`, `is_dev`, `is_test`. Threshold from
`best_f1_threshold(y[is_dev], scores[is_dev])`. One small helper that returns the metric dictionary for
a mask and a threshold; call it for dev, test, and test-and-family.

**Challenge.**

1. Split: sort the unique `snapshot_date` values; the last two are validation.
2. Model: a scikit-learn `Pipeline` with a `ColumnTransformer` (impute + scale numerics, impute +
   one-hot categories) and an unweighted `LogisticRegression`. Do not use `customer_id` or the date.
3. Break-even: offering is worth `p * success_rate * months * price - cost`. Solve for `p`.
4. Policy value: per offered row, `success_rate * months * price * y - cost`; sum, divide by the
   number of customers in the population, multiply by 1,000.
5. In the note, compare mean predicted with observed rate on validation *and* on test. They will not
   tell the same story; say why that matters for a rule of the form `p >= threshold`.
