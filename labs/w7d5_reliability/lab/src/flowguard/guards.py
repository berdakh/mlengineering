"""Model-level guards and the fallback rule. YOU implement these three functions (lab task 1)."""
from __future__ import annotations

from collections.abc import Sequence


def out_of_support(values: Sequence[float], low: float, high: float) -> list[int]:
    """Indices of values outside [low, high] (inclusive bounds: a value equal to a bound is inside).

    [low, high] is the range of the sensor seen in development data. The model still scores such
    values; the API lists their indices so the caller knows those scores are extrapolation.
    """
    raise NotImplementedError("lab task 1")


def fallback_alarms(values: Sequence[float], low: float, high: float) -> list[bool]:
    """Degraded-mode rule: one bool per value, True when the value is outside the envelope [low, high].

    It must need no model state, no burn-in and no bundle, so it still works when those have failed.
    """
    raise NotImplementedError("lab task 1")


def all_finite(scores: Sequence[float]) -> bool:
    """True only if every score is a finite number (no NaN, no +/-inf)."""
    raise NotImplementedError("lab task 1")
