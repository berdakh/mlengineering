"""SERVING path of the logistic candidate (fixed version: the reference solution).

``score_run(run, model)`` must return exactly what the training path (train_features.py) computes:
one score for every row after the run's first ``model["n_burn"]`` rows, rows in time order.

The three skew bugs in the original version and their fixes are recorded in SKEW_REPORT.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def calibrate(burn: pd.DataFrame, sensors: list[str]) -> tuple[np.ndarray, np.ndarray]:
    values = burn[sensors].to_numpy(dtype=float)
    mean, std = values.mean(axis=0), values.std(axis=0)          # ddof=0, as in training
    return mean, np.where(std > 0, std, 1.0)


def featurise(rows: pd.DataFrame, mean: np.ndarray, std: np.ndarray, model: dict) -> np.ndarray:
    z = (rows[model["sensors"]].to_numpy(dtype=float) - mean) / std
    z = np.clip(z, -model["z_clip"], model["z_clip"])           # fix 2: the clip is part of the model
    return np.hstack([z, np.abs(z)])                              # fix 3: [z, |z|], the trained order


def score_run(run: pd.DataFrame, model: dict) -> np.ndarray:
    n_burn = int(model["n_burn"])                                 # fix 1: burn-in comes from the model
    mean, std = calibrate(run.iloc[:n_burn], model["sensors"])
    features = featurise(run.iloc[n_burn:], mean, std, model)
    return features @ np.asarray(model["coef"], dtype=float) + float(model["intercept"])
