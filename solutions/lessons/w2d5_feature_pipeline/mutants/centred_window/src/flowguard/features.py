"""Causal rolling-window features and train-only reference statistics.

Contract of ``causal_rolling_features`` (the checks test exactly this):

* One output row per input row, in the input's order, keyed by ``experiment_id`` and ``t``.
* A feature at row *i* depends only on rows of the SAME experiment and the SAME continuous
  segment whose time is <= that of row *i*. Nothing from the future, nothing from another experiment.
* A new segment starts at the first row of an experiment and after any time gap longer than
  ``max_gap_s`` seconds. ``segment`` (0-based within the experiment) and ``rows_since_reset``
  (1 for the first row of a segment) are returned so downstream code can see the reset.
* Windowed statistics need a full window of ``w`` rows inside the segment; before that they are NaN.
* Names: ``<sensor>__mean_<w>``, ``__std_<w>`` (ddof=1), ``__min_<w>``, ``__max_<w>``,
  ``__slope_<w>`` (least-squares slope per row), ``__ewma_<w>`` (span=w, recursive, no warm-up NaN),
  and ``<sensor>__diff1`` (NaN on the first row of a segment).
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS

FEATURE_VERSION = "1"  # bump whenever the meaning of any feature changes
KEY_COLUMNS = ("experiment_id", "t", "segment", "rows_since_reset")


def _segment_ids(datetimes: pd.Series, max_gap_s: float) -> np.ndarray:
    gap = datetimes.diff().dt.total_seconds().to_numpy()
    return np.cumsum(np.nan_to_num(gap, nan=0.0) > max_gap_s)


def _segment_features(x: pd.DataFrame, windows: Sequence[int]) -> pd.DataFrame:
    """Features for one continuous segment. ``x`` holds only sensor columns, in time order."""
    pos = np.arange(len(x), dtype=float)[:, None]
    parts = {}
    for w in windows:
        roll = x.rolling(window=w, min_periods=w, center=True)
        total = roll.sum()
        parts[f"mean_{w}"] = roll.mean()
        parts[f"std_{w}"] = roll.std()
        parts[f"min_{w}"] = roll.min()
        parts[f"max_{w}"] = roll.max()
        # OLS slope against k = 0..w-1:  (sum k*x - kbar*sum x) / sum (k-kbar)^2
        k_times_x = (x * pos).rolling(window=w, min_periods=w).sum() - (pos - (w - 1)) * total
        parts[f"slope_{w}"] = (k_times_x - (w - 1) / 2.0 * total) / (w * (w * w - 1) / 12.0)
        parts[f"ewma_{w}"] = x.ewm(span=w, adjust=False).mean()
    parts["diff1"] = x.diff()
    out = pd.concat({stat: frame for stat, frame in parts.items()}, axis=1)
    out.columns = [f"{sensor}__{stat}" for stat, sensor in out.columns]
    return out


def feature_names(windows: Sequence[int] = (10, 30, 60), columns: Sequence[str] = SENSOR_COLUMNS) -> list[str]:
    stats = [f"{s}_{w}" for w in windows for s in ("mean", "std", "min", "max", "slope", "ewma")] + ["diff1"]
    return [f"{c}__{s}" for c in columns for s in stats]


def causal_rolling_features(
    tidy: pd.DataFrame,
    windows: Sequence[int] = (10, 30, 60),
    columns: Sequence[str] = SENSOR_COLUMNS,
    max_gap_s: float = 5.0,
) -> pd.DataFrame:
    """Past-and-present-only rolling features, computed separately per experiment and segment."""
    windows = tuple(int(w) for w in windows)
    if not windows or min(windows) < 2:
        raise ValueError("windows must contain integers >= 2")
    names = feature_names(windows, columns)
    pieces = []
    for _, group in tidy.groupby("experiment_id", sort=False):
        group = group.sort_values("datetime", kind="stable")
        segment = _segment_ids(group["datetime"], max_gap_s)
        keys = pd.DataFrame({"experiment_id": group["experiment_id"], "t": group["t"], "segment": segment},
                            index=group.index)
        keys["rows_since_reset"] = keys.groupby("segment").cumcount() + 1
        feats = [_segment_features(group.loc[segment == s, list(columns)].astype(float), windows)
                 for s in np.unique(segment)]
        pieces.append(pd.concat([keys, pd.concat(feats)[names]], axis=1))
    return pd.concat(pieces).loc[tidy.index].reset_index(drop=True)


@dataclass(frozen=True)
class ReferenceStats:
    """Per-feature mean and standard deviation estimated ONCE, on the rows given to ``fit``."""

    mean: dict[str, float]
    std: dict[str, float]

    @classmethod
    def fit(cls, reference: pd.DataFrame, columns: Sequence[str] | None = None) -> "ReferenceStats":
        if columns is None:
            columns = [c for c in reference.columns if c not in KEY_COLUMNS]
        if len(reference) == 0:
            raise ValueError("cannot fit reference statistics on zero rows")
        mean = reference[list(columns)].mean()  # NaN warm-up rows are skipped
        std = reference[list(columns)].std()
        return cls(mean={c: float(mean[c]) for c in columns}, std={c: float(std[c]) for c in columns})

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        """z-scores using the stored statistics; never looks at the statistics of ``features``."""
        out = features.copy()
        for column, mu in self.mean.items():
            sd = self.std[column]
            out[column] = (features[column] - mu) / sd if sd > 0 else 0.0
        return out

    def to_dict(self) -> dict:
        return {"mean": dict(self.mean), "std": dict(self.std)}

    @classmethod
    def from_dict(cls, payload: dict) -> "ReferenceStats":
        return cls(mean=dict(payload["mean"]), std=dict(payload["std"]))


def cache_key(data_sha256: str, params: dict, code_version: str = FEATURE_VERSION) -> str:
    """Content address of a feature table: same data + same code version + same parameters."""
    canonical = json.dumps({"data": data_sha256, "code": code_version, "params": params},
                           sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
