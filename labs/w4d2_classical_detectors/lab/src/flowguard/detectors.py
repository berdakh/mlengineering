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
    # TODO (Task 1): return the column names as a list of str; raise ValueError naming every column
    # that is in FORBIDDEN or whose name mentions elapsed time ("elapsed", or starts with "time").
    raise NotImplementedError("check_columns")


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
        # TODO (Task 2): set columns_ (via check_columns), mean_, scale_ (SD; 1.0 where SD is 0),
        # k_ (n_components, or the smallest k reaching ``variance``), loadings_ (d x k),
        # eigenvalues_ (variances of the k component scores), t2_limit_ and q_limit_ (99th percentiles
        # of the two statistics on the fit rows). Return self.
        raise NotImplementedError("PCADetector.fit")

    def _stats(self, xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        # TODO (Task 2): given STANDARDISED rows xs, return (T2, Q) per row.
        raise NotImplementedError("PCADetector._stats")

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
        # TODO (Task 3)
        raise NotImplementedError("IForestDetector.fit")

    def score(self, features: pd.DataFrame) -> np.ndarray:
        # TODO (Task 3): higher must mean MORE anomalous.
        raise NotImplementedError("IForestDetector.score")


class GBTDetector(_Detector):
    """Supervised gradient-boosted trees (HistGradientBoostingClassifier); score = P(anomaly).

    Early stopping is off so that results depend only on ``seed`` and the data, not on an internal
    random validation split of rows (which would also mix rows of one experiment across that split).
    """

    def __init__(self, max_iter: int = 200, learning_rate: float = 0.1, max_leaf_nodes: int = 31,
                 seed: int = 0):
        self.max_iter, self.learning_rate, self.max_leaf_nodes, self.seed = max_iter, learning_rate, max_leaf_nodes, seed

    def fit(self, features: pd.DataFrame, labels=None) -> "GBTDetector":
        # TODO (Task 4): refuse forbidden columns, require labels (both classes present), fit a
        # HistGradientBoostingClassifier with early stopping OFF and random_state=self.seed.
        raise NotImplementedError("GBTDetector.fit")

    def score(self, features: pd.DataFrame) -> np.ndarray:
        # TODO (Task 4): probability of the anomalous class.
        raise NotImplementedError("GBTDetector.score")
