"""Baseline anomaly scorers.

Contract shared by every scorer:
* ``fit(train_tidy)`` learns from the sensor columns of the rows it is given and returns ``self``.
  It never reads the label columns.
* ``score(tidy)`` returns one finite float per row; HIGHER means MORE anomalous. The score of a row
  depends only on that row and on what ``fit`` learned, never on the other rows being scored.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS

_SENSORS = list(SENSOR_COLUMNS)


class ConstantScorer:
    """The floor: every row gets the same score. Any metric it reaches is free."""

    def fit(self, train_tidy: pd.DataFrame) -> "ConstantScorer":
        return self

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        return np.zeros(len(tidy), dtype=float)


class _Standardiser:
    def fit(self, train_tidy: pd.DataFrame):
        x = train_tidy[_SENSORS].to_numpy(dtype=float)
        if len(x) < 2:
            raise ValueError("need at least two rows to fit")
        self.mean_ = x.mean(axis=0)
        std = x.std(axis=0)
        self.std_ = np.where(std > 0, std, 1.0)      # a sensor that never moved carries no evidence
        return self

    def _z(self, tidy: pd.DataFrame) -> np.ndarray:
        x = tidy[_SENSORS].to_numpy(dtype=float)
        if len(x) > 1:                               # "standardise the data" before scoring it
            std = x.std(axis=0)
            return (x - x.mean(axis=0)) / np.where(std > 0, std, 1.0)
        return (x - self.mean_) / self.std_


class SingleSensorZScorer(_Standardiser):
    """|z| of one named sensor."""

    def __init__(self, column: str):
        if column not in _SENSORS:
            raise ValueError(f"unknown sensor {column!r}")
        self.column = column

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        return np.abs(self._z(tidy)[:, _SENSORS.index(self.column)])


class MaxAbsZScorer(_Standardiser):
    """max over sensors of |z|: alarms when any single sensor leaves its normal range."""

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        return np.abs(self._z(tidy)).max(axis=1)


class MahalanobisScorer(_Standardiser):
    """Mahalanobis distance to the training mean (the square root of Hotelling's T^2 statistic).

    The correlation matrix R of the training data is shrunk towards the identity,
    R_s = (1 - shrinkage) * R + shrinkage * I, which keeps it invertible and limits the influence of
    poorly estimated small eigenvalues. shrinkage = 1 ignores correlations entirely.
    """

    def __init__(self, shrinkage: float = 0.1):
        if not 0.0 <= shrinkage <= 1.0:
            raise ValueError("shrinkage must be in [0, 1]")
        self.shrinkage = shrinkage

    def fit(self, train_tidy: pd.DataFrame) -> "MahalanobisScorer":
        super().fit(train_tidy)
        z = self._z(train_tidy)
        corr = (z.T @ z) / len(z)
        np.fill_diagonal(corr, 1.0)                  # constant sensors would leave a 0 here
        corr = (1.0 - self.shrinkage) * corr + self.shrinkage * np.eye(len(_SENSORS))
        self.precision_ = np.linalg.pinv(corr)
        return self

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        z = self._z(tidy)
        d2 = np.einsum("ij,jk,ik->i", z, self.precision_, z)
        return np.sqrt(np.clip(d2, 0.0, None))


def burn_in_scores(make_scorer: Callable[[], object], tidy: pd.DataFrame, n_burn: int) -> np.ndarray:
    """Per-experiment calibration: fit a fresh scorer on the first ``n_burn`` rows of each experiment
    and score all rows of that experiment. Rows are returned in the order of ``tidy``.

    The first ``n_burn`` rows are scored in-sample and must be excluded from evaluation.
    """
    tidy = tidy.reset_index(drop=True)
    scores = np.full(len(tidy), np.nan)
    for _, group in tidy.groupby("experiment_id", sort=False):
        group = group.sort_values("t", kind="stable")
        if len(group) <= n_burn:
            raise ValueError(f"experiment {group['experiment_id'].iloc[0]!r} has only {len(group)} rows")
        scorer = make_scorer().fit(group.iloc[:n_burn])
        scores[group.index.to_numpy()] = scorer.score(group)
    return scores
