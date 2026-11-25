"""Causal rolling-window features and train-only reference statistics.  (w2d5 lab - YOUR CODE)

Contract of ``causal_rolling_features`` (the checks test exactly this):

* One output row per input row, in the input's order, keyed by ``experiment_id`` and ``t``.
* A feature at row *i* depends only on rows of the SAME experiment and the SAME continuous
  segment whose time is <= that of row *i*. Nothing from the future, nothing from another experiment.
* A new segment starts at the first row of an experiment and after any time gap longer than
  ``max_gap_s`` seconds. ``segment`` (0-based within the experiment) and ``rows_since_reset``
  (1 for the first row of a segment) are returned so downstream code can see the reset.
* Windowed statistics need a full window of ``w`` rows inside the segment; before that they are NaN.
* Names: ``<sensor>__mean_<w>``, ``__std_<w>`` (ddof=1), ``__min_<w>``, ``__max_<w>``,
  ``__slope_<w>`` (least-squares slope per row), ``__ewma_<w>`` (span=w, recursive
  ``y_i = a*x_i + (1-a)*y_{i-1}`` with ``a = 2/(w+1)``, ``y_0 = x_0``, no warm-up NaN),
  and ``<sensor>__diff1`` (NaN on the first row of a segment).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from flowguard.data import SENSOR_COLUMNS

FEATURE_VERSION = "1"  # bump whenever the meaning of any feature changes
KEY_COLUMNS = ("experiment_id", "t", "segment", "rows_since_reset")


def causal_rolling_features(
    tidy: pd.DataFrame,
    windows: Sequence[int] = (10, 30, 60),
    columns: Sequence[str] = SENSOR_COLUMNS,
    max_gap_s: float = 5.0,
) -> pd.DataFrame:
    """Past-and-present-only rolling features, computed separately per experiment and segment.

    Returns KEY_COLUMNS followed by the feature columns. Must not modify ``tidy``.
    """
    raise NotImplementedError("Task 1-3 of the w2d5 lab")


@dataclass(frozen=True)
class ReferenceStats:
    """Per-feature mean and standard deviation estimated ONCE, on the rows given to ``fit``."""

    mean: dict[str, float]
    std: dict[str, float]

    @classmethod
    def fit(cls, reference: pd.DataFrame, columns: Sequence[str] | None = None) -> "ReferenceStats":
        """Estimate statistics on ``reference``. Default columns: everything except KEY_COLUMNS.

        NaN warm-up rows are skipped. Zero rows -> ValueError.
        """
        raise NotImplementedError("Task 4 of the w2d5 lab")

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with the fitted columns replaced by z-scores (other columns unchanged)."""
        raise NotImplementedError("Task 4 of the w2d5 lab")

    def to_dict(self) -> dict:
        return {"mean": dict(self.mean), "std": dict(self.std)}

    @classmethod
    def from_dict(cls, payload: dict) -> "ReferenceStats":
        return cls(mean=dict(payload["mean"]), std=dict(payload["std"]))


def cache_key(data_sha256: str, params: dict, code_version: str = FEATURE_VERSION) -> str:
    """Content address of a feature table. Decide what must be part of the identity (Task 5)."""
    raise NotImplementedError("Task 5 of the w2d5 lab")
