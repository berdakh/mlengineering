"""The shipped detector family. SNAPSHOT written to the w4d5/w5d1 description; given to you.

``BurnInZ`` scores each sample by the largest burn-in |z| over its sensors:

* **Calibration.** The first ``n_burn`` samples of a run are assumed normal. Their mean and
  population standard deviation (``ddof=0``; a constant sensor gets ``sigma = 1``) are frozen.
* **Score.** ``max_j |x_j - mu_j| / sigma_j`` over ``sensors``; NaN for the burn-in rows.
* **Alarms.** samples with ``score >= threshold`` are flagged, then turned into alarm events with
  ``min_duration`` and ``merge_gap`` (``flowguard.evaluation.extract_events``).

With ``sensors=("flow_rate",)`` this is exactly the model chosen in w4d5 (threshold 7.2441,
min_duration 30, merge_gap 10). Because each run is normalised by its own burn-in, the score is
unchanged when a sensor's readings are transformed by ``a*x + b`` with ``a > 0``: a recalibrated
sensor moves the raw input distribution but not a single score.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS
from flowguard.evaluation import extract_events

MODEL_TYPE = "flowguard.burn_in_maxz"


@dataclass(frozen=True)
class BurnInZ:
    name: str = "flowguard"
    version: str = "1.0.0"
    sensors: tuple[str, ...] = ("flow_rate",)
    n_burn: int = 100
    threshold: float = 7.244130714098134
    min_duration: int = 30
    merge_gap: int = 10
    metadata: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sensors", tuple(self.sensors))
        unknown = [s for s in self.sensors if s not in SENSOR_COLUMNS]
        if not self.sensors or unknown:
            raise ValueError(f"sensors must be a non-empty subset of SENSOR_COLUMNS; unknown: {unknown}")
        if self.n_burn < 2:
            raise ValueError("n_burn must be at least 2")
        if not np.isfinite(self.threshold):
            raise ValueError("threshold must be finite")
        if self.min_duration < 1 or self.merge_gap < 0:
            raise ValueError("min_duration must be >= 1 and merge_gap >= 0")

    # ------------------------------------------------------------------ contract
    @property
    def required_columns(self) -> list[str]:
        return ["datetime", *self.sensors]

    @property
    def label(self) -> str:
        return f"{self.name}-{self.version}"

    # ------------------------------------------------------------------ scoring
    def score_run(self, run: pd.DataFrame) -> np.ndarray:
        """Scores for one run in row order. ``run`` is one machine's samples from the start of
        monitoring, strictly increasing in ``datetime``, finite in every sensor used."""
        missing = [c for c in self.required_columns if c not in run.columns]
        if missing:
            raise ValueError(f"run is missing columns {missing}")
        times = pd.to_datetime(run["datetime"]).to_numpy()
        if len(times) > 1 and not (np.diff(times) > np.timedelta64(0, "ns")).all():
            raise ValueError("datetime must be strictly increasing")
        x = run[list(self.sensors)].to_numpy(dtype=float)
        if not np.isfinite(x).all():
            raise ValueError("sensor values must be finite")
        scores = np.full(len(x), np.nan)
        if len(x) <= self.n_burn:
            return scores
        burn = x[: self.n_burn]
        mu = burn.mean(axis=0)
        sigma = burn.std(axis=0)
        sigma = np.where(sigma > 0, sigma, 1.0)
        scores[self.n_burn:] = (np.abs(x[self.n_burn:] - mu) / sigma).max(axis=1)
        return scores

    def flags(self, scores: np.ndarray) -> np.ndarray:
        scores = np.asarray(scores, dtype=float)
        return np.isfinite(scores) & (scores >= self.threshold)

    def alarm_events(self, run: pd.DataFrame) -> list[tuple[int, int]]:
        """Alarm events as (start_row, end_row) with the end exclusive, in row positions of ``run``."""
        return [tuple(e) for e in extract_events(self.flags(self.score_run(run)).astype(int),
                                                 min_duration=self.min_duration, merge_gap=self.merge_gap)]

    # ------------------------------------------------------------------ (de)serialisation
    def params(self) -> dict:
        d = asdict(self)
        d.pop("metadata")
        d["sensors"] = list(self.sensors)
        return d

    @classmethod
    def from_params(cls, params: dict, metadata: dict | None = None) -> "BurnInZ":
        unknown = set(params) - {f for f in cls.__dataclass_fields__ if f != "metadata"}
        if unknown:
            raise ValueError(f"unknown model parameters {sorted(unknown)}")
        return cls(**params, metadata=dict(metadata or {}))


def score_experiments(model: BurnInZ, tidy: pd.DataFrame) -> np.ndarray:
    """Scores for every row of a tidy table (many experiments), aligned with ``tidy``'s rows."""
    out = np.full(len(tidy), np.nan)
    positions = np.arange(len(tidy))
    for _, idx in tidy.groupby("experiment_id", sort=False).indices.items():
        idx = np.asarray(idx)
        order = idx[np.argsort(tidy["t"].to_numpy()[idx], kind="stable")]
        out[positions[order]] = model.score_run(tidy.iloc[order])
    return out
