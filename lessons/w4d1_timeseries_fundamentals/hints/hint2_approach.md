# Hint 2 — approach

**Lab.**

* `acf`: `d = x - x.mean()`, `denom = d @ d`, then for each `k >= 1` the sum of `d[k:] * d[:-k]`.
* `ARForecaster.fit`: `lags = self._design(x)` has `n - p` rows; the target is `x[p:]`. Add a column of
  ones in front, solve with `np.linalg.lstsq`, split the solution into `intercept_` and `coef_`,
  then `self._set_sigma(x)` (it calls your `predict`).
* `predict`: allocate `np.full(len(x), np.nan)` and fill entries `p:` with `intercept_ + _design(x) @ coef_`.
* `cusum`: two running floats, a Python loop is fine at these sizes; skip non-finite inputs by
  writing the previous statistic again.

**Challenge.**

* Work on `np.log(sales)`; per store, sort by date; `n_fit = number of dates < fit_end`.
* Residual scale: standard deviation of residuals on the fit window only (ignore NaNs).
* Score = `max(0, residual / sigma)` (one-sided).
* `choose`: split the development dates at their median date; for each method fit on dates before it,
  scan thresholds on the validation dates, keep the method and threshold with the best F1.
* `evaluate`: call `store_scores(df, method, dev_end)` and compare with the labels on dates `>= dev_end`.
