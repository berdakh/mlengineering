"""Deployable candidates for the w4d5 model choice. SNAPSHOT, given to you; you do not need to edit it.

Every candidate is used the same way in the field:

1. ``fit(dev_tidy)`` learns whatever is shared across machines (only the supervised candidate uses
   it; the others return ``self``). This is the *retraining* step and is timed.
2. ``calibrate(burn_in_rows)`` is called when monitoring of a new run starts, with the first
   ``n_burn`` rows of that run (all normal by the project's convention). It returns a **step**.
3. ``step.score(rows)`` scores any number of later rows of that run: one float per row, higher means
   more anomalous, and a row's score depends only on that row and the calibration. The step is the
   deployed artifact: it is what is timed per sample and what is serialised to measure size.

``score_experiments(candidate, tidy, n_burn)`` runs 2-3 on every experiment of ``tidy`` and returns
the scores in ``tidy``'s row order; the first ``n_burn`` rows of each experiment are scored in
sample and must be excluded from evaluation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression

from flowguard.baselines import MahalanobisScorer, SingleSensorZScorer
from flowguard.data import SENSOR_COLUMNS

_SENSORS = list(SENSOR_COLUMNS)
Z_CLIP = 20.0   # a sensor 1000 SD away is "far"; unclipped z lets one sensor dominate the fit (as in w3d5)


class _Unsupervised:
    """Wraps a w2d6 scorer factory: calibration = fitting a fresh scorer on the burn-in rows."""

    supervised = False

    def __init__(self, name: str, factory, dependencies: str, explanation: str):
        self.name, self._factory = name, factory
        self.dependencies, self.explanation = dependencies, explanation

    def fit(self, dev_tidy: pd.DataFrame | None = None) -> "_Unsupervised":
        return self

    def calibrate(self, burn_in_rows: pd.DataFrame):
        return self._factory().fit(burn_in_rows)


class _IsolationForestStep:
    """Isolation forest on burn-in standardised sensors. Higher = more anomalous."""

    def __init__(self, n_estimators: int, random_state: int):
        self.n_estimators, self.random_state = n_estimators, random_state

    def fit(self, rows: pd.DataFrame) -> "_IsolationForestStep":
        x = rows[_SENSORS].to_numpy(dtype=float)
        self.mean_, std = x.mean(axis=0), x.std(axis=0)
        self.std_ = np.where(std > 0, std, 1.0)
        self.forest_ = IsolationForest(n_estimators=self.n_estimators, random_state=self.random_state)
        self.forest_.fit((x - self.mean_) / self.std_)
        return self

    def score(self, rows: pd.DataFrame) -> np.ndarray:
        z = (rows[_SENSORS].to_numpy(dtype=float) - self.mean_) / self.std_
        return -self.forest_.score_samples(z)


class _LogisticStep:
    """Burn-in z of each sensor and its absolute value -> shared logistic regression."""

    def __init__(self, mean: np.ndarray, std: np.ndarray, model: LogisticRegression):
        self.mean_, self.std_, self.model_ = mean, std, model

    def score(self, rows: pd.DataFrame) -> np.ndarray:
        z = np.clip((rows[_SENSORS].to_numpy(dtype=float) - self.mean_) / self.std_, -Z_CLIP, Z_CLIP)
        return self.model_.decision_function(np.hstack([z, np.abs(z)]))


class SupervisedLogistic:
    """Logistic regression on per-run standardised sensors, trained on labelled development runs.

    The only candidate that learns across machines; the only one that needs labels to retrain.
    """

    supervised = True
    name = "logistic (supervised)"
    dependencies = "numpy, scikit-learn"
    explanation = "8 signed weights per |z| and z; readable, but learned from labelled faults"

    def __init__(self, n_burn: int, C: float = 1.0):
        self.n_burn, self.C = n_burn, C

    @staticmethod
    def _standardise(rows: pd.DataFrame, burn: pd.DataFrame):
        x = burn[_SENSORS].to_numpy(dtype=float)
        mean, std = x.mean(axis=0), x.std(axis=0)
        return mean, np.where(std > 0, std, 1.0)

    def fit(self, dev_tidy: pd.DataFrame) -> "SupervisedLogistic":
        feats, labels = [], []
        for _, g in dev_tidy.groupby("experiment_id", sort=False):
            g = g.sort_values("t", kind="stable")
            mean, std = self._standardise(g, g.iloc[: self.n_burn])
            rest = g.iloc[self.n_burn:]
            z = np.clip((rest[_SENSORS].to_numpy(dtype=float) - mean) / std, -Z_CLIP, Z_CLIP)
            feats.append(np.hstack([z, np.abs(z)]))
            labels.append(rest["anomaly"].to_numpy())
        y = np.concatenate(labels)
        if len(np.unique(y)) < 2:
            raise ValueError("supervised training needs both classes in the development rows")
        self.model_ = LogisticRegression(C=self.C, max_iter=2000).fit(np.vstack(feats), y)
        return self

    def calibrate(self, burn_in_rows: pd.DataFrame) -> _LogisticStep:
        if not hasattr(self, "model_"):
            raise RuntimeError("call fit() on labelled development data first")
        mean, std = self._standardise(burn_in_rows, burn_in_rows)
        return _LogisticStep(mean, std, self.model_)


def candidates(n_burn: int, seed: int = 0) -> list:
    """The four candidates compared in w4d5, simplest first."""
    return [
        _Unsupervised("flow-rate |z|", lambda: SingleSensorZScorer("flow_rate"), "numpy",
                      "one sensor's distance from its own start-up level"),
        _Unsupervised("Mahalanobis", lambda: MahalanobisScorer(shrinkage=0.1), "numpy",
                      "joint distance over 8 sensors; per-sensor contributions can be shown"),
        _Unsupervised("isolation forest", lambda: _IsolationForestStep(100, seed), "numpy, scikit-learn",
                      "path length in 100 random trees; no per-sensor reason"),
        SupervisedLogistic(n_burn),
    ]


def score_experiments(candidate, tidy: pd.DataFrame, n_burn: int) -> np.ndarray:
    """Calibrate on each experiment's first ``n_burn`` rows and score all its rows (``tidy`` order)."""
    tidy = tidy.reset_index(drop=True)
    scores = np.full(len(tidy), np.nan)
    for _, g in tidy.groupby("experiment_id", sort=False):
        g = g.sort_values("t", kind="stable")
        if len(g) <= n_burn:
            raise ValueError(f"experiment {g['experiment_id'].iloc[0]!r} has only {len(g)} rows")
        step = candidate.calibrate(g.iloc[:n_burn])
        scores[g.index.to_numpy()] = step.score(g)
    return scores
