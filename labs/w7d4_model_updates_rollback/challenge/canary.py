"""Canary analysis with a stated stopping rule (w7d4 challenge). Implement the two functions.

The rule is in README.md. Useful pieces: ``scipy.stats.chi2.ppf`` for exact Poisson bounds,
``scipy.stats.norm.ppf`` for the Wilson interval's z.
"""
from __future__ import annotations

import pandas as pd

RULE = {"max_alerts_per_hour": 1.0, "error_margin": 0.01, "min_canary_hours": 24,
        "min_canary_requests": 2000, "confidence": 0.95}


def decide(log: pd.DataFrame, rule: dict = RULE) -> dict:
    raise NotImplementedError


def run_canary(log: pd.DataFrame, rule: dict = RULE) -> dict:
    raise NotImplementedError
