"""Classical detectors behind one interface.

Contract (the checks rely on it)
--------------------------------
* ``fit(features, labels=None)`` learns from the rows it is given and returns ``self``.
  ``features`` is a DataFrame of feature columns only. Semi-supervised detectors (PCA, isolation
  forest) ignore ``labels``: the caller passes rows believed normal. The supervised detector (GBT)
  requires ``labels``.
* ``score(features)`` returns one finite float per row; HIGHER = MORE anomalous. A row's score depends
  only on that row and on what ``fit`` learned, never on the other rows being scored.
* No detector accepts a column that identifies time, the unit or the label (``FORBIDDEN``): such a
  column lets a model learn the experimental protocol (see the elapsed-time finding in project/README.md).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest

FORBIDDEN = frozenset({"t", "datetime", "anomaly", "changepoint", "experiment_id", "family", "label"})


def check_columns(features: pd.DataFrame) -> list[str]:
    """Return the column list, refusing identifiers, labels and anything that names elapsed time."""
    cols = [str(c) for c in features.columns]
    bad = [c for c in cols if c in FORBIDDEN or "elapsed" in c.lower() or c.lower().startswith("time")]
    if bad:
        raise ValueError(f"forbidden feature columns: {bad}")
    return cols


class _Detector:
    columns_: list[str]

    def _matrix(self, features: pd.DataFrame) -> np.ndarray:
        missing = [c for c in self.columns_ if c not in features.columns]
        if missing:
            raise ValueError(f"missing feature columns: {missing[:5]}")
        return features[self.columns_].to_numpy(dtype=float)


class PCADetector(_Detector):
    """PCA model of normal data with two statistics.

    With standardised data x (mean and SD from the fit rows), loadings P (d x k) of the first k
    principal components and their variances lambda_1..k:

        T^2 = sum_j (x P)_j^2 / lambda_j        distance WITHIN the retained subspace
        Q   = || x - x P P^T ||^2                squared prediction error (SPE): distance FROM it

    k is the smallest number of components explaining at least ``variance`` of the total, unless
    ``n_components`` is given. ``t2_limit_`` and ``q_limit_`` are the 99th percentiles of each
    statistic on the fit rows (empirical control limits).
    """

    def __init__(self, variance: float = 0.9, n_components: int | None = None, statistic: str = "q"):
        if statistic not in ("q", "t2", "sum"):
            raise ValueError("statistic must be 'q', 't2' or 'sum'")
        self.variance, self.n_components, self.statistic = variance, n_components, statistic

    def fit(self, features: pd.DataFrame, labels=None) -> "PCADetector":
        self.columns_ = check_columns(features)
        x = self._matrix(features)
        self.mean_ = x.mean(axis=0)
        sd = x.std(axis=0)
        self.scale_ = np.where(sd > 0, sd, 1.0)
        xs = (x - self.mean_) / self.scale_
        _, s, vt = np.linalg.svd(xs, full_matrices=False)
        var = s ** 2 / (len(xs) - 1)
        if self.n_components is not None:
            k = int(self.n_components)
        else:
            k = int(np.searchsorted(np.cumsum(var) / var.sum(), self.variance) + 1)
        k = max(1, min(k, len(var)))
        self.k_ = k
        self.loadings_ = vt[:k].T
        self.eigenvalues_ = np.maximum(var[:k], 1e-12)
        t2, q = self._stats(xs)
        self.t2_limit_ = float(np.quantile(t2, 0.99))
        self.q_limit_ = float(np.quantile(q, 0.99))
        return self

    def _stats(self, xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        proj = xs @ self.loadings_
        t2 = np.sum(proj ** 2 / self.eigenvalues_, axis=1)
        resid = xs - proj @ self.loadings_.T
        return t2, np.sum(resid ** 2, axis=1)

    def score_t2(self, features: pd.DataFrame) -> np.ndarray:
        return self._stats((self._matrix(features) - self.mean_) / self.scale_)[0]

    def score_q(self, features: pd.DataFrame) -> np.ndarray:
        return self._stats((self._matrix(features) - self.mean_) / self.scale_)[1]

    def score(self, features: pd.DataFrame) -> np.ndarray:
        t2, q = self._stats((self._matrix(features) - self.mean_) / self.scale_)
        if self.statistic == "t2":
            return t2
        if self.statistic == "q":
            return q
        return t2 / self.t2_limit_ + q / self.q_limit_          # each relative to its own limit


class IForestDetector(_Detector):
    """Isolation forest. Score = minus sklearn's ``score_samples`` (so higher = more anomalous).

    ``contamination`` is deliberately not exposed: in sklearn it only sets the threshold of
    ``predict``, i.e. it is an alarm threshold chosen without data. Thresholds are chosen on
    development data instead.
    """

    def __init__(self, n_estimators: int = 200, max_samples: int | str = 256, seed: int = 0):
        self.n_estimators, self.max_samples, self.seed = n_estimators, max_samples, seed

    def fit(self, features: pd.DataFrame, labels=None) -> "IForestDetector":
        self.columns_ = check_columns(features)
        self.model_ = IsolationForest(n_estimators=self.n_estimators, max_samples=self.max_samples,
                                      random_state=self.seed).fit(self._matrix(features))
        return self

    def score(self, features: pd.DataFrame) -> np.ndarray:
        return self.model_.score_samples(self._matrix(features))


class GBTDetector(_Detector):
    """Supervised gradient-boosted trees (HistGradientBoostingClassifier); score = P(anomaly).

    Early stopping is off so that results depend only on ``seed`` and the data, not on an internal
    random validation split of rows (which would also mix rows of one experiment across that split).
    """

    def __init__(self, max_iter: int = 200, learning_rate: float = 0.1, max_leaf_nodes: int = 31,
                 seed: int = 0):
        self.max_iter, self.learning_rate, self.max_leaf_nodes, self.seed = max_iter, learning_rate, max_leaf_nodes, seed

    def fit(self, features: pd.DataFrame, labels=None) -> "GBTDetector":
        self.columns_ = check_columns(features)
        if labels is None:
            raise ValueError("GBTDetector is supervised: labels are required")
        y = np.asarray(labels).astype(int).ravel()
        if len(y) != len(features):
            raise ValueError("labels must have one value per row")
        if len(np.unique(y)) < 2:
            raise ValueError("labels must contain both classes")
        self.model_ = HistGradientBoostingClassifier(
            max_iter=self.max_iter, learning_rate=self.learning_rate, max_leaf_nodes=self.max_leaf_nodes,
            early_stopping=False, random_state=self.seed).fit(self._matrix(features), y)
        return self

    def score(self, features: pd.DataFrame) -> np.ndarray:
        return self.model_.predict_proba(self._matrix(features))[:, 1]
