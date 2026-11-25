# Hint 3 — partial implementation

Decisive lines are left as `...`.

## Lab

```python
def acf(x, nlags):
    x = _as_series(x)
    if nlags < 0 or nlags >= len(x):
        raise ValueError("need 0 <= nlags < len(x)")
    d = ...
    denom = float(d @ d)
    if denom <= _EPS:
        raise ValueError("constant series")
    return np.array([1.0] + [float(d[k:] @ d[:-k]) / ... for k in range(1, nlags + 1)])


class ARForecaster(_Forecaster):
    def fit(self, x):
        x = _as_series(x)
        # validation: length and finiteness (ValueError)
        lags = self._design(x)
        design = np.column_stack([..., lags])
        beta, *_ = np.linalg.lstsq(design, ..., rcond=None)
        self.intercept_, self.coef_ = float(beta[0]), beta[1:]
        self._set_sigma(x)
        return self

    def predict(self, x):
        x = _as_series(x)
        pred = np.full(len(x), np.nan)
        if len(x) > self.p:
            pred[self.p:] = ...
        return pred


def cusum(z, k=0.5):
    z = _as_series(z)
    if k < 0:
        raise ValueError("k must be >= 0")
    up = down = 0.0
    out = np.empty(len(z))
    for i, v in enumerate(z):
        if np.isfinite(v):
            up = max(0.0, ...)
            down = max(0.0, ...)
        out[i] = max(up, down)
    return out
```

## Challenge

```python
def store_scores(df, method, fit_end):
    out = np.full(len(df), np.nan)
    frame = df.reset_index(drop=True)
    for _, g in frame.groupby("store", sort=False):
        g = g.sort_values("date", kind="stable")
        x = np.log(g["sales"].to_numpy(dtype=float))
        n_fit = int((g["date"] < fit_end).sum())
        pred = np.full(len(x), np.nan)
        if method == "seasonal_naive":
            pred[7:] = ...
        else:
            ...                                   # AR(7) fitted on x[:n_fit], predicting every row
        resid = x - pred
        sigma = np.nanstd(resid[:n_fit], ddof=1)
        out[g.index.to_numpy()] = ...             # one-sided, standardised
    return out
```
