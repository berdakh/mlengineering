"""Causal window features on burn-in-normalised sensors. SNAPSHOT-style helper, given in w4d2.

For every experiment separately, in time order:

* ``z_<sensor>``: (x - mean) / std, with mean and std from the first ``n_burn`` rows of that
  experiment (the per-experiment reference of docs/maintainers/flowguard-spec.md, amendments);
* ``mean<w>_<sensor>``, ``std<w>_<sensor>``: trailing (past-and-present) rolling mean and standard
  deviation of that z over the last ``w`` rows.

No column depends on rows after the current one or on another experiment, and none encodes time:
``t`` and ``datetime`` are kept only as identifiers for evaluation and are never feature columns.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS

ID_COLUMNS = ("experiment_id", "family", "t", "datetime", "anomaly", "changepoint")
CLIP = 20.0


def window_features(tidy: pd.DataFrame, n_burn: int = 100, windows: Sequence[int] = (10, 30)) -> pd.DataFrame:
    """Return a frame aligned with ``tidy`` (same index) holding the ID columns and the features."""
    out = []
    for _, g in tidy.groupby("experiment_id", sort=False):
        g = g.sort_values("t", kind="stable")
        if len(g) <= n_burn:
            raise ValueError(f"experiment {g['experiment_id'].iloc[0]!r} has only {len(g)} rows")
        x = g[list(SENSOR_COLUMNS)].to_numpy(dtype=float)
        mu = x[:n_burn].mean(axis=0)
        sd = x[:n_burn].std(axis=0)
        z = np.clip((x - mu) / np.where(sd > 0, sd, 1.0), -CLIP, CLIP)
        cols = {f"z_{s}": z[:, j] for j, s in enumerate(SENSOR_COLUMNS)}
        zf = pd.DataFrame(z, columns=list(SENSOR_COLUMNS), index=g.index)
        for w in windows:
            roll = zf.rolling(w, min_periods=1)
            m, s = roll.mean(), roll.std().fillna(0.0)
            for sensor in SENSOR_COLUMNS:
                cols[f"mean{w}_{sensor}"] = m[sensor].to_numpy()
                cols[f"std{w}_{sensor}"] = s[sensor].to_numpy()
        frame = pd.DataFrame(cols, index=g.index)
        for c in ID_COLUMNS:
            if c in g.columns:
                frame.insert(0, c, g[c].to_numpy())
        out.append(frame)
    return pd.concat(out).loc[tidy.index]


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c not in ID_COLUMNS]
