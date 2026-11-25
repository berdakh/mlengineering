"""The shipped detector: burn-in |z| of one sensor, alarm when score >= threshold.

This module is the ONLY place the score is computed. Evaluation, batch inference and the API all call
``ZScoreModel.score``; that is what makes their outputs identical (w5d6 three-way parity).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class ZScoreModel:
    sensor: str
    n_burn_in: int
    threshold: float
    min_duration: int
    merge_gap: int
    model_version: str

    def score(self, burn_in, values) -> np.ndarray:
        """|values - mean(burn_in)| / std(burn_in), population std (ddof 0); zero spread -> std 1."""
        burn = np.asarray(burn_in, dtype=float)
        x = np.asarray(values, dtype=float)
        if burn.size < 2:
            raise ValueError("burn_in needs at least two values")
        std = burn.std()
        return np.abs(x - burn.mean()) / (std if std > 0 else 1.0)

    def above_threshold(self, scores) -> np.ndarray:
        return np.asarray(scores) >= self.threshold

    def to_dict(self) -> dict:
        return asdict(self)
