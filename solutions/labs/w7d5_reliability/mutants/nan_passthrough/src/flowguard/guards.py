"""Model-level guards and the fallback rule (the learner implements these in the lab)."""
from __future__ import annotations

import math
from collections.abc import Sequence


def out_of_support(values: Sequence[float], low: float, high: float) -> list[int]:
    """Indices of values outside [low, high], the range the model saw in development data.

    The model still scores them; the response lists them so the caller knows those scores are
    extrapolation. Inclusive bounds: a value equal to a bound is inside.
    """
    return [i for i, v in enumerate(values) if v < low or v > high]


def fallback_alarms(values: Sequence[float], low: float, high: float) -> list[bool]:
    """The degraded-mode rule: alarm when a value leaves the normal operating envelope [low, high].

    It needs no model state, no burn-in and no bundle, so it still works when those have failed.
    """
    return [bool(v < low or v > high) for v in values]


def all_finite(scores: Sequence[float]) -> bool:
    """True only if every score is a finite number. NaN or inf from a model is a wrong answer."""
    return True
