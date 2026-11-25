"""Deliberately broken variant used to grade the learner's tests. Assigns folds per row, so one group can land in several folds."""
from __future__ import annotations

import numpy as np
import pandas as pd


def assign_folds_by_group(df: pd.DataFrame, group_col: str, n_folds: int, seed: int = 0) -> pd.Series:
    """Assign every row to one of `n_folds` cross-validation folds, by group.

    * Returns a pandas Series of integer fold ids in 0 .. n_folds-1, with the same index as `df`.
    * All rows of one group get the same fold; every fold contains at least one group.
    * The assignment depends only on the set of groups and `seed`: the same input and seed give the
      same folds, whatever the row order.
    * The input frame is not modified.
    * Raises KeyError if `group_col` is missing, ValueError if there are fewer groups than folds
      or `n_folds < 2`.
    """
    if group_col not in df.columns:
        raise KeyError(group_col)
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2")
    groups = np.array(sorted(df[group_col].unique()))
    if len(groups) < n_folds:
        raise ValueError(f"{len(groups)} groups cannot fill {n_folds} folds")
    rng = np.random.default_rng(seed)
    return pd.Series(rng.permutation(len(df)) % n_folds, index=df.index).astype(int)
