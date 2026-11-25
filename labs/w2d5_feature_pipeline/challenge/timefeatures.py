"""Independent challenge (w2d5): causal time-based window features for irregular sampling.

The full specification and acceptance criteria are in README.md next to this file.
"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def time_window_features(
    df: pd.DataFrame, windows_s: Sequence[float] = (30.0, 120.0), max_gap_s: float = 20.0
) -> pd.DataFrame:
    raise NotImplementedError
