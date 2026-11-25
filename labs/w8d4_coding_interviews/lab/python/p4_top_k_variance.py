"""P4 (medium, aggregation + heap): the k noisiest sensors. Starter: implement the function; the docstring is the specification."""
from __future__ import annotations

from typing import Hashable, Iterable


def top_k_variance(readings: Iterable[tuple[Hashable, float]], k: int) -> list:
    """The k sensors with the largest population variance of their readings.

    Sensors with fewer than two readings are ignored. Variances that agree to 12 significant digits are
    ties (floating-point noise must not decide the order); ties are broken by sensor id ascending.
    Returns at most k ids, highest variance first. Values may be large (around 1e9) with a small spread.
    Required: about O(n + s log s) for n readings and s sensors.
    """
    raise NotImplementedError("w8d4: implement this")
