"""Validation folds that match the store-demand deployment question (challenge, w3d2)."""
from __future__ import annotations

import numpy as np
import pandas as pd

LABEL_WEEKS = 4


def deployment_folds(panel: pd.DataFrame, cutoffs: list[int], horizon_weeks: int = 8,
                     label_weeks: int = LABEL_WEEKS) -> list[dict]:
    """One fold per cut-off week c, mirroring "retrain at c, use for the next ``horizon_weeks``".

    train      rows whose label was fully observed by c:  week + label_weeks <= c
    validation rows the model would be used on:           c < week <= c + horizon_weeks, label present
      val_known  ... of stores that have at least one training row
      val_new    ... of stores that have none (opened after c, or so recently that no label was complete)
    All values are sorted arrays of row positions in ``panel``.
    """
    week = panel["week"].to_numpy()
    store = panel["store_id"].to_numpy()
    has_label = panel["demand_next4"].notna().to_numpy()
    position = np.arange(len(panel))
    folds = []
    for c in cutoffs:
        train = has_label & (week <= c)
        val = has_label & (week > c) & (week <= c + horizon_weeks)
        if not train.any() or not val.any():
            raise ValueError(f"cut-off {c} leaves no training or no validation rows")
        known = np.isin(store, np.unique(store[train]))
        folds.append({"cutoff": int(c), "train": position[train],
                      "val_known": position[val & known], "val_new": position[val & ~known]})
    return folds
