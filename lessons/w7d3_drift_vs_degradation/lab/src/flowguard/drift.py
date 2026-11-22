"""Input-drift statistics and a calibrated drift monitor. SNAPSHOT written to the w7d2 description.

Given to you. Three statistics compare a current window with a reference sample of one column:

* **PSI** (population stability index) over ``bins`` quantile bins of the reference:
  ``sum_i (c_i - r_i) * ln(c_i / r_i)`` with proportions floored at ``eps``.
* **KS** two-sample statistic ``sup_x |F_cur(x) - F_ref(x)|``.
* **Wasserstein-1** distance (in the column's units; scale-dependent).

Thresholds are **calibrated, not folklore**: ``DriftMonitor.calibrate`` draws ``n_calib`` contiguous
chunks of the window length from the reference itself (contiguous, so autocorrelation is kept) and sets
each threshold at the ``quantile`` of the statistic over those chunks. A window is flagged when any
column exceeds its threshold. The false-alarm rate on stable data is then roughly ``1 - quantile`` per
column and window, which is what you budget for. A flag says *the inputs changed*; it says nothing
about whether the model got worse (that is w7d3).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import ks_2samp, wasserstein_distance


def psi(reference, current, bins: int = 10, eps: float = 1e-4) -> float:
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:  # constant reference
        return float(0.0 if np.allclose(cur, ref[0]) else np.inf)
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    c = np.histogram(cur, edges)[0] / len(cur)
    r, c = np.maximum(r, eps), np.maximum(c, eps)
    return float(np.sum((c - r) * np.log(c / r)))


def ks(reference, current) -> float:
    return float(ks_2samp(np.asarray(reference, float), np.asarray(current, float)).statistic)


def wasserstein(reference, current) -> float:
    return float(wasserstein_distance(np.asarray(reference, float), np.asarray(current, float)))


STATISTICS = {"psi": psi, "ks": ks, "wasserstein": wasserstein}


@dataclass
class DriftMonitor:
    reference: dict[str, np.ndarray]
    statistic: str = "psi"
    quantile: float = 0.99
    n_calib: int = 200
    seed: int = 0
    thresholds: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.statistic not in STATISTICS:
            raise ValueError(f"statistic must be one of {sorted(STATISTICS)}")
        self.reference = {k: np.asarray(v, dtype=float) for k, v in self.reference.items()}

    def calibrate(self, window_size: int) -> "DriftMonitor":
        fn = STATISTICS[self.statistic]
        rng = np.random.default_rng(self.seed)
        for col, ref in self.reference.items():
            if window_size >= len(ref):
                raise ValueError(f"reference for {col} is shorter than one window")
            starts = rng.integers(0, len(ref) - window_size, size=self.n_calib)
            values = [fn(ref, ref[s:s + window_size]) for s in starts]
            self.thresholds[col] = float(np.quantile(values, self.quantile))
        return self

    def check(self, window: dict[str, np.ndarray]) -> dict:
        if not self.thresholds:
            raise RuntimeError("calibrate the monitor before checking windows")
        fn = STATISTICS[self.statistic]
        per = {}
        for col, ref in self.reference.items():
            value = fn(ref, np.asarray(window[col], dtype=float))
            per[col] = {"value": value, "threshold": self.thresholds[col],
                        "flagged": bool(value > self.thresholds[col])}
        return {"drift": any(v["flagged"] for v in per.values()), "statistic": self.statistic,
                "per_column": per}
