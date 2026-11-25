"""Group-aware splitting: every unit lands entirely in train or entirely in test."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

logger = logging.getLogger(__name__)


def group_train_test_split(
    features: pd.DataFrame, test_fraction: float = 0.3, seed: int = 7, group_column: str = "unit_id"
) -> tuple[np.ndarray, np.ndarray]:
    """Return positional (train_idx, test_idx) with no group on both sides."""
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_fraction, random_state=seed)
    train_idx, test_idx = next(splitter.split(features, groups=features[group_column]))
    logger.info("split seed=%d n_train=%d n_test=%d test_groups=%s", seed, len(train_idx), len(test_idx),
                sorted(features[group_column].iloc[test_idx].unique().tolist()))
    return train_idx, test_idx
