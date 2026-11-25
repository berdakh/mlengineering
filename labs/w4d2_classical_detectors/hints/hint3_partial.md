# Hint 3 — partial implementation

Decisive lines are left as `...`.

## Lab

```python
def check_columns(features):
    cols = [str(c) for c in features.columns]
    bad = [c for c in cols if ...]
    if bad:
        raise ValueError(f"forbidden feature columns: {bad}")
    return cols


class PCADetector(_Detector):
    def fit(self, features, labels=None):
        self.columns_ = check_columns(features)
        x = self._matrix(features)
        self.mean_ = x.mean(axis=0)
        sd = x.std(axis=0)
        self.scale_ = np.where(sd > 0, sd, 1.0)
        xs = (x - self.mean_) / self.scale_
        _, s, vt = np.linalg.svd(xs, full_matrices=False)
        var = s ** 2 / (len(xs) - 1)
        k = ...                                     # n_components, or the variance rule
        self.k_ = k
        self.loadings_ = vt[:k].T
        self.eigenvalues_ = np.maximum(var[:k], 1e-12)
        t2, q = self._stats(xs)
        self.t2_limit_, self.q_limit_ = ..., ...
        return self

    def _stats(self, xs):
        proj = xs @ self.loadings_
        t2 = ...
        q = ...
        return t2, q
```

## Challenge

```python
def grouped_oof_ap(kind, train, seed=0):
    labelled = train["label"].notna().to_numpy()
    scores = np.full(len(train), np.nan)
    for fit_idx, held_idx in GroupKFold(n_splits=5).split(train, groups=...):
        model = _fit(kind, train.iloc[fit_idx], seed)     # forest: all rows; GBT: labelled rows only
        scores[held_idx] = model.score(train.iloc[held_idx])
    return average_precision_score(..., scores[labelled])
```
