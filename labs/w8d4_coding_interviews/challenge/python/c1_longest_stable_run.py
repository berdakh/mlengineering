"""C1 (mock): the longest stable stretch of a signal. Starter: the docstring is the specification."""
from __future__ import annotations


def longest_stable_run(values: list[float], tolerance: float) -> tuple[int, int]:
    """(start, length) of the longest contiguous run whose max - min <= tolerance.

    The earliest such run wins ties. Empty input -> (0, 0). Negative tolerance -> ValueError.
    Required: O(n) for 300,000 values.
    """
    raise NotImplementedError("w8d4 challenge: implement this")
