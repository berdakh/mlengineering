"""The TRAINING path of the logistic candidate, exactly as it was evaluated in w4d5.

Given; do not edit. This is the arithmetic of flowguard.detectors.SupervisedLogistic and _LogisticStep
(w4d5 snapshot), restated without scikit-learn so it can be read in one screen:

* a run is calibrated on its first ``n_burn`` rows: mean and POPULATION standard deviation (ddof=0)
  of each sensor; a standard deviation of 0 becomes 1.0;
* every later row becomes z = (x - mean) / std per sensor, clipped to [-z_clip, z_clip];
* the feature vector is [z_1 .. z_8, |z_1| .. |z_8|] (sensors in ``model["sensors"]`` order);
* the score is features @ coef + intercept (scikit-learn's ``decision_function``).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def training_scores(run: pd.DataFrame, model: dict) -> np.ndarray:
    """Scores for rows ``n_burn ..`` of one run, rows in time order. Length ``len(run) - n_burn``."""
    sensors, n_burn = model["sensors"], int(model["n_burn"])
    x = run[sensors].to_numpy(dtype=float)
    burn = x[:n_burn]
    mean, std = burn.mean(axis=0), burn.std(axis=0)
    std = np.where(std > 0, std, 1.0)
    z = np.clip((x[n_burn:] - mean) / std, -model["z_clip"], model["z_clip"])
    features = np.hstack([z, np.abs(z)])
    return features @ np.asarray(model["coef"], dtype=float) + float(model["intercept"])
