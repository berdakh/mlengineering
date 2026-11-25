"""Leak probes for the project. They do not prove the absence of leakage; they catch known kinds.

* ``audit_features``        - refuse feature names that can never be model inputs.
* ``time_monotone_columns`` - find features that are a clock in disguise.
* ``clock_probe``           - how well does elapsed time alone "detect" anomalies under this protocol?
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from flowguard.metrics import pr_auc

FORBIDDEN_FEATURES = ("t", "datetime", "anomaly", "changepoint", "experiment_id", "family")


def audit_features(columns: Iterable[str], forbidden: Iterable[str] = FORBIDDEN_FEATURES) -> None:
    """Raise ValueError naming every column that must not be a model input.

    Labels, identifiers and the clock (``t``, ``datetime``) are forbidden by name. Call this on the
    exact column list handed to the model, immediately before fitting.
    """
    bad = sorted(set(columns) & set(forbidden))
    if bad:
        raise ValueError(f"forbidden feature columns: {bad}")


def time_monotone_columns(features: pd.DataFrame, tidy: pd.DataFrame, threshold: float = 0.95) -> list[str]:
    """Feature columns whose rank correlation with elapsed time is near +-1 inside experiments.

    ``features`` is row-aligned with ``tidy``. For each column the Spearman correlation with ``t`` is
    computed within every experiment; a column is reported when the median absolute correlation is
    at least ``threshold``. Constant columns are never reported.
    """
    if len(features) != len(tidy):
        raise ValueError("features must have one row per row of tidy")
    experiment = tidy["experiment_id"].to_numpy()
    t = tidy["t"].to_numpy(dtype=float)
    flagged = []
    for column in features.columns:
        x = features[column].to_numpy(dtype=float)
        rhos = []
        for e in pd.unique(experiment):
            m = (experiment == e) & np.isfinite(x)
            if m.sum() < 3 or np.ptp(x[m]) == 0:
                continue
            rx, rt = pd.Series(x[m]).rank().to_numpy(), pd.Series(t[m]).rank().to_numpy()
            rhos.append(abs(np.corrcoef(rx, rt)[0, 1]))
        if rhos and float(np.median(rhos)) >= threshold:
            flagged.append(column)
    return flagged


def clock_probe(tidy: pd.DataFrame, experiments: Iterable[str] | None = None, burn_in: int = 0) -> dict:
    """Score every row by elapsed time ``t`` and report how much "skill" that buys.

    Returns ``pr_auc_clock`` (average precision of the score ``t``), ``prevalence`` (the average
    precision of a constant score) and ``lift`` (their difference), computed on rows with
    ``t >= burn_in`` of the chosen experiments, plus the spread of anomaly onset positions.
    A large lift means the protocol itself predicts the label: a model can score well by learning
    when faults are usually injected, and any feature that tracks time inherits that advantage.
    """
    rows = tidy if experiments is None else tidy[tidy["experiment_id"].isin(list(experiments))]
    rows = rows[rows["t"] >= burn_in]
    y = rows["anomaly"].to_numpy()
    if len(rows) == 0 or y.sum() == 0:
        raise ValueError("clock_probe needs at least one anomalous row")
    onsets = rows[rows["anomaly"] == 1].groupby("experiment_id")["t"].min().to_numpy()
    prevalence = float(y.mean())
    auc = pr_auc(y, rows["t"].to_numpy(dtype=float))
    return {
        "n_rows": int(len(rows)), "n_experiments": int(rows["experiment_id"].nunique()),
        "prevalence": prevalence, "pr_auc_clock": auc, "lift": auc - prevalence,
        "onset_t_min": int(onsets.min()), "onset_t_median": float(np.median(onsets)),
        "onset_t_max": int(onsets.max()),
    }
