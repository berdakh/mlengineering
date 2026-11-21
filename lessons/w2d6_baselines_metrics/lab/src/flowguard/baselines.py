"""Baseline anomaly scorers.

Contract shared by every scorer:
* ``fit(train_tidy)`` learns from the SENSOR columns of the rows it is given and returns ``self``.
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
    """The floor: every row gets the same score."""

    def fit(self, train_tidy: pd.DataFrame) -> "ConstantScorer":
        raise NotImplementedError("lab task 3")

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError("lab task 3")


class SingleSensorZScorer:
    """|z| of one named sensor, standardised with the training mean and standard deviation."""

    def __init__(self, column: str):
        self.column = column

    def fit(self, train_tidy: pd.DataFrame) -> "SingleSensorZScorer":
        raise NotImplementedError("lab task 3")

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError("lab task 3")


class MaxAbsZScorer:
    """max over sensors of |z|: alarms when any single sensor leaves its normal range."""

    def fit(self, train_tidy: pd.DataFrame) -> "MaxAbsZScorer":
        raise NotImplementedError("lab task 3")

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError("lab task 3")


class MahalanobisScorer:
    """Mahalanobis distance to the training mean (square root of Hotelling's T^2).

    Must work with no constructor arguments. Decide how to keep the covariance invertible
    (lesson section 2.3) and what to do with a sensor whose training variance is zero.
    """

    def fit(self, train_tidy: pd.DataFrame) -> "MahalanobisScorer":
        raise NotImplementedError("lab task 3")

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError("lab task 3")


def burn_in_scores(make_scorer: Callable[[], object], tidy: pd.DataFrame, n_burn: int) -> np.ndarray:
    """GIVEN. Per-experiment calibration: fit a fresh scorer on the first ``n_burn`` rows of each
    experiment and score all rows of that experiment. Rows are returned in the order of ``tidy``.

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
