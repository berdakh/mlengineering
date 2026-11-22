"""Causal features for the selection lab. SNAPSHOT in the spirit of the w2d5/w2d6 modules.

Given to you in this lab; you do not need to edit it. Everything here uses only the current row and
earlier rows of the same experiment. Position in the recording (``t``, ``datetime``) is never a
feature: on SKAB it predicts the label by itself (docs/FLOWGUARD_SPEC.md, amendments).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS

WINDOWS = (10, 30, 60)
Z_CLIP = 20.0


def burn_in_normalise(tidy: pd.DataFrame, n_burn_in: int = 100) -> pd.DataFrame:
    """z-score every sensor against the first ``n_burn_in`` rows of its own experiment, clipped.

    Returns a frame with columns ``z_<sensor>`` aligned to ``tidy``. Rows with ``t < n_burn_in``
    are in-sample for the statistics and must be excluded from fitting and evaluation.
    """
    out = pd.DataFrame(index=tidy.index, columns=[f"z_{s}" for s in SENSOR_COLUMNS], dtype=float)
    for _, group in tidy.groupby("experiment_id", sort=False):
        group = group.sort_values("t", kind="stable")
        if len(group) <= n_burn_in:
            raise ValueError(f"experiment {group['experiment_id'].iloc[0]!r} has only {len(group)} rows")
        head = group.iloc[:n_burn_in][list(SENSOR_COLUMNS)]
        std = head.std(ddof=0).replace(0.0, np.nan)
        z = ((group[list(SENSOR_COLUMNS)] - head.mean()) / std).fillna(0.0).clip(-Z_CLIP, Z_CLIP)
        out.loc[group.index] = z.to_numpy()
    return out


def selection_features(tidy: pd.DataFrame, n_burn_in: int = 100, windows=WINDOWS) -> pd.DataFrame:
    """``z_<s>`` plus, for each window w, trailing mean ``m<w>_<s>`` and trailing std ``s<w>_<s>`` of z.

    Windows are trailing (rows t-w+1..t) and are computed per experiment, so no value depends on a
    later row or on another experiment. The result has the identifying columns of ``tidy`` first.
    """
    z = burn_in_normalise(tidy, n_burn_in)
    parts = [tidy[["experiment_id", "family", "t", "anomaly"]], z]
    grouped = z.groupby(tidy["experiment_id"], sort=False)
    for w in windows:
        mean = grouped.rolling(w, min_periods=1).mean().reset_index(level=0, drop=True).reindex(z.index)
        std = grouped.rolling(w, min_periods=2).std(ddof=0).reset_index(level=0, drop=True).reindex(z.index).fillna(0.0)
        parts.append(mean.rename(columns=lambda c, w=w: c.replace("z_", f"m{w}_")))
        parts.append(std.rename(columns=lambda c, w=w: c.replace("z_", f"s{w}_")))
    return pd.concat(parts, axis=1)


def columns_for(window: int) -> list[str]:
    """Feature columns used by a model with trailing window ``window`` (0 = instantaneous z only)."""
    cols = [f"z_{s}" for s in SENSOR_COLUMNS]
    if window:
        cols += [f"m{window}_{s}" for s in SENSOR_COLUMNS] + [f"s{window}_{s}" for s in SENSOR_COLUMNS]
    return cols


def all_feature_columns(windows=WINDOWS) -> list[str]:
    cols = [f"z_{s}" for s in SENSOR_COLUMNS]
    for w in windows:
        cols += [f"m{w}_{s}" for s in SENSOR_COLUMNS] + [f"s{w}_{s}" for s in SENSOR_COLUMNS]
    return cols
