"""Input monitoring: schema checks, missingness and distribution shift. STARTER (w7d2): implement the functions marked TODO (tasks 1-3).

Three separate questions, answered separately:

1. **Is the input well-formed?** A value that is not finite or lies outside ``limits`` is a schema
   violation: counted, reported, and EXCLUDED from the statistics below.
2. **Is data missing?** NaN in a sensor is missingness, not a violation: the share per sensor and window
   is reported and alerts above ``max_missing``.
3. **Has the distribution moved?** Per sensor and window, against a fixed reference sample:

   * PSI  = sum_i (q_i - p_i) ln(q_i / p_i) over bins cut at reference quantiles, p reference shares,
     q current shares, both floored at ``EPS`` (a bin with no current rows would otherwise give inf).
   * KS   = sup_x |F_ref(x) - F_cur(x)| (two-sample Kolmogorov-Smirnov statistic; no p-value).
   * W1   = integral |F_ref(x) - F_cur(x)| dx (Wasserstein-1, in the sensor's own units).

Thresholds are not folklore: ``calibrate_thresholds`` picks them so that, on windows of stable data,
the share of windows with ANY distribution alert is about ``target_far``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from flowguard.limits import SENSOR_LIMITS

EPS = 1e-4
STATS = ("psi", "ks", "w1")


# ------------------------------------------------------------------------------------- statistics
def _clean(x) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    return x[np.isfinite(x)]


def psi_from_proportions(p, q, eps: float = EPS) -> float:
    """PSI of two share vectors over the same bins: sum (q - p) ln(q / p), shares floored at ``eps``.

    TODO w7d2 (task 1).
    """
    raise NotImplementedError("TODO w7d2 task 1: psi_from_proportions")


def bin_edges(reference, bins: int = 10) -> np.ndarray:
    """Interior bin edges at the reference's k/bins quantiles (duplicates removed: discrete sensors)."""
    ref = _clean(reference)
    return np.unique(np.quantile(ref, np.arange(1, bins) / bins))


def psi(reference, current, bins: int = 10, eps: float = EPS) -> float:
    """PSI of ``current`` against ``reference`` using ``bin_edges(reference, bins)`` (open outer bins).

    Assign values with ``np.searchsorted(edges, x, side="right")``; shares are counts / size. Non-finite
    values are ignored (use ``_clean``). Return NaN if either sample is empty. TODO w7d2 (task 1).
    """
    raise NotImplementedError("TODO w7d2 task 1: psi")


def ks_stat(reference, current) -> float:
    """Two-sample KS statistic: sup over x of |F_ref(x) - F_cur(x)| (empirical CDFs). TODO w7d2 (task 1).

    Must equal ``scipy.stats.ks_2samp(...).statistic`` for any sizes and ties. NaN if a sample is empty.
    """
    raise NotImplementedError("TODO w7d2 task 1: ks_stat")


def wasserstein1(reference, current) -> float:
    """Wasserstein-1: the area between the two empirical CDFs, in data units. TODO w7d2 (task 1).

    Must equal ``scipy.stats.wasserstein_distance`` for any sizes and ties. NaN if a sample is empty.
    """
    raise NotImplementedError("TODO w7d2 task 1: wasserstein1")


STAT_FUNCS = {"psi": psi, "ks": ks_stat, "w1": wasserstein1}


# ---------------------------------------------------------------------------------------- monitor
@dataclass
class DriftReport:
    window_index: int
    n_rows: int
    n_schema_violations: int
    missing: dict[str, float]
    stats: dict[str, dict[str, float]]
    alerts: list[tuple[str, str, float, float]] = field(default_factory=list)  # (sensor, kind, value, thr)

    @property
    def drift_alert(self) -> bool:
        return any(kind in STATS for _, kind, _, _ in self.alerts)

    @property
    def schema_alert(self) -> bool:
        return self.n_schema_violations > 0


def split_violations(frame: pd.DataFrame, sensors, limits=SENSOR_LIMITS) -> tuple[pd.DataFrame, pd.Series]:
    """(rows without violations, boolean Series marking violating rows). TODO w7d2 (task 2).

    A row violates the schema if any sensor value is +-inf or outside ``limits[sensor]``.
    NaN is missingness, NOT a violation.
    """
    raise NotImplementedError("TODO w7d2 task 2: split_violations")


class DriftMonitor:
    """Tumbling-window input monitor.

    Rows are buffered; every ``window`` rows RECEIVED (violations included, so the cadence follows time,
    not data quality) one ``DriftReport`` is produced. Statistics use the window's non-violating rows.
    ``thresholds[sensor][stat]`` triggers a drift alert when the statistic exceeds it; sensors or stats
    without a threshold are computed but never alert.
    """

    def __init__(self, reference: pd.DataFrame, sensors, window: int,
                 thresholds: dict[str, dict[str, float]] | None = None,
                 limits=SENSOR_LIMITS, max_missing: float = 0.05, bins: int = 10):
        if window < 2:
            raise ValueError("window must be at least 2 rows")
        self.sensors = tuple(sensors)
        missing_cols = [s for s in self.sensors if s not in reference.columns]
        if missing_cols:
            raise ValueError(f"reference lacks sensors {missing_cols}")
        clean_ref, _ = split_violations(reference, self.sensors, limits)
        self.reference = {s: _clean(clean_ref[s]) for s in self.sensors}
        self.window, self.thresholds, self.limits = window, thresholds or {}, limits
        self.max_missing, self.bins = max_missing, bins
        self._buffer: list[pd.DataFrame] = []
        self._buffered = 0
        self._index = 0

    def window_stats(self, frame: pd.DataFrame) -> DriftReport:
        """Statistics and alerts for one window of rows (no buffering). TODO w7d2 (task 2).

        1. Raise ValueError if a sensor column is absent (that is a schema failure of the whole batch).
        2. ``split_violations``; count violating rows.
        3. Per sensor: missing share among the clean rows; the three statistics of the clean, finite
           values against ``self.reference[sensor]`` (NaN if fewer than 2 values; psi with ``self.bins``).
        4. Alerts: (sensor, stat, value, threshold) when a finite statistic exceeds
           ``self.thresholds[sensor][stat]``; (sensor, "missing", share, self.max_missing) when the
           missing share exceeds ``self.max_missing``.
        5. Return ``DriftReport(self._index, len(frame), ...)`` and increment ``self._index``.
        """
        raise NotImplementedError("TODO w7d2 task 2: DriftMonitor.window_stats")

    def update(self, batch: pd.DataFrame) -> list[DriftReport]:
        """Add rows; return the reports of every window completed by this batch (possibly none)."""
        reports = []
        start = 0
        while start < len(batch):
            take = min(self.window - self._buffered, len(batch) - start)
            self._buffer.append(batch.iloc[start:start + take])
            self._buffered += take
            start += take
            if self._buffered == self.window:
                reports.append(self.window_stats(pd.concat(self._buffer, ignore_index=True)))
                self._buffer, self._buffered = [], 0
        return reports


# -------------------------------------------------------------------------------------- calibration
def stable_windows(runs, window: int):
    """Tumbling windows of ``window`` rows from each stable run (a trailing partial window is dropped)."""
    for run in runs:
        for start in range(0, len(run) - window + 1, window):
            yield run.iloc[start:start + window]


def calibrate_thresholds(reference: pd.DataFrame, stable_runs, sensors, window: int,
                         stat: str = "w1", target_far: float = 0.05, bins: int = 10) -> dict[str, dict[str, float]]:
    """Per-sensor thresholds for ``stat`` so that about ``target_far`` of stable windows raise ANY alert.

    TODO w7d2 (task 3). Compute ``stat`` for every sensor on every window of ``stable_windows(stable_runs,
    window)`` (a monitor with no thresholds and ``window_stats`` does this), then take for each sensor a
    quantile of the values. Which quantile makes the WINDOW-level rate (any of m sensors) about
    ``target_far``? Use ``np.quantile(..., method="higher")``. Raise ValueError for an unknown ``stat``
    or when there are no stable windows. Return ``{sensor: {stat: threshold}}``.
    """
    raise NotImplementedError("TODO w7d2 task 3: calibrate_thresholds")


def alarm_rate(reports) -> float:
    """Share of reports with at least one distribution alert (schema and missingness excluded)."""
    reports = list(reports)
    return float(np.mean([r.drift_alert for r in reports])) if reports else float("nan")
