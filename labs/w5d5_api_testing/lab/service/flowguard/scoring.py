"""The shipped detector: burn-in flow-rate |z| with an alert-budget threshold (chosen in w4d5)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class ZScoreModel:
    """|x - mean(burn_in)| / std(burn_in) for one sensor; alarm when the score is >= threshold.

    ``std`` is the population standard deviation (ddof = 0), as in training (w2d6, w4d5). A burn-in
    with zero spread carries no scale information; it is treated as std = 1.
    """

    sensor: str
    n_burn_in: int
    threshold: float
    min_duration: int
    merge_gap: int
    model_version: str

    def score(self, burn_in, values) -> np.ndarray:
        burn = np.asarray(burn_in, dtype=float)
        x = np.asarray(values, dtype=float)
        if burn.size < 2:
            raise ValueError("burn_in needs at least two values")
        mean = burn.mean()
        std = burn.std()
        if std <= 0:
            std = 1.0
        return np.abs(x - mean) / std

    def above_threshold(self, scores: np.ndarray) -> np.ndarray:
        return np.asarray(scores) >= self.threshold

    def to_dict(self) -> dict:
        return asdict(self)
