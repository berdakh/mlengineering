"""SERVING path of the logistic candidate, as written by a colleague for the batch scorer.

``score_run(run, model)`` must return exactly what the training path (train_features.py) computes:
one score for every row after the run's first ``model["n_burn"]`` rows, rows in time order.

It runs, it returns floats of a plausible size, and its alarms look reasonable on a dashboard.
It also contains three training/serving-skew bugs. Find them, fix them here, write a parity test
(test_parity.py) that fails on this original version, and record each bug in SKEW_REPORT.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BURN_IN = 60          # rows used to calibrate a run


def calibrate(burn: pd.DataFrame, sensors: list[str]) -> tuple[np.ndarray, np.ndarray]:
    values = burn[sensors].to_numpy(dtype=float)
    mean, std = values.mean(axis=0), values.std(axis=0)
    return mean, np.where(std > 0, std, 1.0)


def featurise(rows: pd.DataFrame, mean: np.ndarray, std: np.ndarray, model: dict) -> np.ndarray:
    z = (rows[model["sensors"]].to_numpy(dtype=float) - mean) / std
    return np.hstack([np.abs(z), z])


def score_run(run: pd.DataFrame, model: dict) -> np.ndarray:
    mean, std = calibrate(run.iloc[:BURN_IN], model["sensors"])
    features = featurise(run.iloc[BURN_IN:], mean, std, model)
    return features @ np.asarray(model["coef"], dtype=float) + float(model["intercept"])
