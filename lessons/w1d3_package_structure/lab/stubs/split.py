"""Group-aware splitting: every unit lands entirely in train or entirely in test."""
from __future__ import annotations

import numpy as np
import pandas as pd


def group_train_test_split(
    features: pd.DataFrame, test_fraction: float = 0.3, seed: int = 7, group_column: str = "unit_id"
) -> tuple[np.ndarray, np.ndarray]:
    """Return positional (train_idx, test_idx); no group appears on both sides.

    Must reproduce the script's split for test_fraction=0.3, seed=7.
    """
    raise NotImplementedError
