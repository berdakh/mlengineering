# Hint 2 — approach

**Lab.**

* `fit`: `x = features[columns].to_numpy(float)`; `mean_`, `scale_`; `xs = (x - mean_) / scale_`;
  `u, s, vt = np.linalg.svd(xs, full_matrices=False)`; variances `s**2 / (n - 1)`; `k` from the cumulative
  share (`np.searchsorted` on `cumsum / total` is one way; the smallest k whose share is >= variance);
  `loadings_ = vt[:k].T`; limits are `np.quantile(..., 0.99)` of the statistics of `xs`.
* `_stats`: `t = xs @ P`; `T2 = sum(t**2 / eigenvalues_, axis=1)`; `Q = sum((xs - t @ P.T)**2, axis=1)`.
* Isolation forest: negate `score_samples`.
* GBT: validate columns and labels before fitting; `predict_proba(...)[:, 1]`.

**Challenge.**

* Features: the seven numeric columns; never the identifiers or the label.
* Estimate: `GroupKFold(n_splits=5)` with `groups=train["customer_id"]`; for each fold fit on the other
  customers (forest: all their rows; GBT: their labelled rows), score the held-out customers, and compute
  average precision on the held-out *labelled* rows only, pooled over folds.
* Choose the higher estimate; refit the chosen method on all training rows; set every `random_state`.
