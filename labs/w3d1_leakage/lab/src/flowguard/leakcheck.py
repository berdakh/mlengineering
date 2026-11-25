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
    raise NotImplementedError("w3d1 lab: implement audit_features")


def time_monotone_columns(features: pd.DataFrame, tidy: pd.DataFrame, threshold: float = 0.95) -> list[str]:
    """Feature columns whose rank correlation with elapsed time is near +-1 inside experiments.

    ``features`` is row-aligned with ``tidy``. For each column the Spearman correlation with ``t`` is
    computed within every experiment; a column is reported when the median absolute correlation is
    at least ``threshold``. Constant columns are never reported.
    """
    raise NotImplementedError("w3d1 lab: implement time_monotone_columns")


def clock_probe(tidy: pd.DataFrame, experiments: Iterable[str] | None = None, burn_in: int = 0) -> dict:
    """Score every row by elapsed time ``t`` and report how much "skill" that buys.

    Returns ``pr_auc_clock`` (average precision of the score ``t``), ``prevalence`` (the average
    precision of a constant score) and ``lift`` (their difference), computed on rows with
    ``t >= burn_in`` of the chosen experiments, plus the spread of anomaly onset positions.
    A large lift means the protocol itself predicts the label: a model can score well by learning
    when faults are usually injected, and any feature that tracks time inherits that advantage.
    """
    raise NotImplementedError("w3d1 lab: implement clock_probe")
