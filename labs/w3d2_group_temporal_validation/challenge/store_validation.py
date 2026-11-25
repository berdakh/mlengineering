"""Validation folds that match the store-demand deployment question (challenge, w3d2).

Read challenge/README.md first. Implement `deployment_folds`; do not change its signature.
"""
from __future__ import annotations

import pandas as pd

LABEL_WEEKS = 4


def deployment_folds(panel: pd.DataFrame, cutoffs: list[int], horizon_weeks: int = 8,
                     label_weeks: int = LABEL_WEEKS) -> list[dict]:
    """One dict per cut-off week, in the order of ``cutoffs``:

        {"cutoff": c, "train": ..., "val_known": ..., "val_new": ...}

    The three values are sorted integer arrays of ROW POSITIONS in ``panel`` (0 .. len(panel) - 1).
    Raise ValueError if a cut-off leaves no training rows or no validation rows.
    """
    raise NotImplementedError("your design goes here")
