"""The shipped detector as one object. SNAPSHOT written to the w5d1 description; given to you.

The model chosen in w4d5 is the flow-rate |z| detector:

* **Calibration.** When monitoring of a run starts, the first ``n_burn`` samples are assumed normal
  (the project convention since w2d5). Their mean ``mu`` and population standard deviation ``sigma``
  (``ddof=0``; a sensor that never moved gets ``sigma = 1``) are frozen.
* **Score.** Every later sample gets ``|x - mu| / sigma``. Higher means more anomalous.
* **Operating point.** ``threshold``, ``min_duration`` and ``merge_gap`` were chosen on development
  data for an alert budget of one false alarm per 8 hours (w3d4, w4d5).

``score_batch`` is the reference that streaming (w5d3) and the API (w5d4) must agree with.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS


@dataclass(frozen=True)
class Detector:
    sensor: str = "flow_rate"
    n_burn: int = 100
    threshold: float = 7.244130714098134
    min_duration: int = 30
    merge_gap: int = 10
    version: str = "flowguard-z-1.0.0"

    def __post_init__(self) -> None:
        if self.sensor not in SENSOR_COLUMNS:
            raise ValueError(f"unknown sensor {self.sensor!r}")
        if self.n_burn < 2:
            raise ValueError("n_burn must be at least 2")
        if not np.isfinite(self.threshold):
            raise ValueError("threshold must be finite")

    @staticmethod
    def calibration(values: np.ndarray) -> tuple[float, float]:
        """(mu, sigma) of the burn-in values; sigma is the population SD, 1.0 if it is 0."""
        values = np.asarray(values, dtype=float)
        mu = float(values.mean())
        sigma = float(values.std())
        return mu, (sigma if sigma > 0 else 1.0)

    def score_batch(self, run: pd.DataFrame) -> np.ndarray:
        """Scores for one run, in row order: NaN for the first ``n_burn`` rows, |z| afterwards.

        ``run`` must be one machine's samples from the start of monitoring, strictly increasing in
        ``datetime``, with no missing or non-finite values in ``self.sensor``.
        """
        if self.sensor not in run.columns or "datetime" not in run.columns:
            raise ValueError(f"run needs columns 'datetime' and {self.sensor!r}")
        times = pd.to_datetime(run["datetime"]).to_numpy()
        if len(times) > 1 and not (np.diff(times) > np.timedelta64(0, "ns")).all():
            raise ValueError("datetime must be strictly increasing")
        x = run[self.sensor].to_numpy(dtype=float)
        if not np.isfinite(x).all():
            raise ValueError(f"{self.sensor} contains missing or non-finite values")
        scores = np.full(len(x), np.nan)
        if len(x) <= self.n_burn:
            return scores
        mu, sigma = self.calibration(x[: self.n_burn])
        scores[self.n_burn:] = np.abs(x[self.n_burn:] - mu) / sigma
        return scores

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, params: dict) -> "Detector":
        unknown = set(params) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown detector parameters {sorted(unknown)}")
        return cls(**params)
