"""Input monitoring: schema checks, missingness and distribution shift. REFERENCE SOLUTION (w7d2).

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
    """PSI of two share vectors over the same bins; shares are floored at ``eps``.

    Equal to KL(q||p) + KL(p||q) on the floored shares, hence symmetric in (p, q).
    """
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.nansum((q - p) * np.log(q / p)))


def bin_edges(reference, bins: int = 10) -> np.ndarray:
    """Interior bin edges at the reference's k/bins quantiles (duplicates removed: discrete sensors)."""
    ref = _clean(reference)
    return np.unique(np.quantile(ref, np.arange(1, bins) / bins))


def psi(reference, current, bins: int = 10, eps: float = EPS) -> float:
    """PSI of ``current`` against ``reference`` with reference-quantile bins (open outer bins).

    A value equal to an edge goes to the bin on the edge's right (``searchsorted(..., side="right")``).
    """
    ref, cur = _clean(reference), _clean(current)
    if ref.size == 0 or cur.size == 0:
        return float("nan")
    edges = bin_edges(ref, bins)
    k = edges.size + 1
    p = np.bincount(np.searchsorted(edges, ref, side="right"), minlength=k) / ref.size
    q = np.bincount(np.searchsorted(edges, cur, side="right"), minlength=k) / cur.size
    return psi_from_proportions(p, q, eps)


def _ecdfs(ref: np.ndarray, cur: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    grid = np.sort(np.concatenate([ref, cur]))
    f_ref = np.searchsorted(np.sort(ref), grid, side="right") / ref.size
    f_cur = np.searchsorted(np.sort(cur), grid, side="right") / cur.size
    return grid, f_ref, f_cur


def ks_stat(reference, current) -> float:
    """Two-sample KS statistic: the largest vertical gap between the two empirical CDFs."""
    ref, cur = _clean(reference), _clean(current)
    if ref.size == 0 or cur.size == 0:
        return float("nan")
    _, f_ref, f_cur = _ecdfs(ref, cur)
    return float(np.max(np.abs(f_ref - f_cur)))


def wasserstein1(reference, current) -> float:
    """Wasserstein-1 distance: the area between the two empirical CDFs (units of the data)."""
    ref, cur = _clean(reference), _clean(current)
    if ref.size == 0 or cur.size == 0:
        return float("nan")
    grid, f_ref, f_cur = _ecdfs(ref, cur)
    return float(np.sum(np.abs(f_ref - f_cur)[:-1] * np.diff(grid)))


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
    """(values with violations set to NaN-free clean rows only, boolean Series of violating rows).

    A row violates the schema if any sensor value is +-inf or outside ``limits``. NaN is missingness,
    not a violation.
    """
    bad = pd.Series(False, index=frame.index)
    for s in sensors:
        x = frame[s].astype(float)
        lo, hi = limits[s]
        bad |= np.isinf(x) | (x.notna() & ((x < lo) | (x > hi)))
    return frame.loc[~bad], bad


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
        """Statistics and alerts for one window of rows (no buffering)."""
        for s in self.sensors:
            if s not in frame.columns:
                raise ValueError(f"input lacks sensor column {s!r} (schema)")
        clean, bad = split_violations(frame, self.sensors, self.limits)
        missing = {s: float(clean[s].isna().mean()) if len(clean) else 0.0 for s in self.sensors}
        stats, alerts = {}, []
        for s in self.sensors:
            cur = _clean(clean[s])
            stats[s] = {name: (fn(self.reference[s], cur, self.bins) if name == "psi"
                               else fn(self.reference[s], cur)) if cur.size >= 2 else float("nan")
                        for name, fn in STAT_FUNCS.items()}
            for name, thr in self.thresholds.get(s, {}).items():
                v = stats[s].get(name, float("nan"))
                if np.isfinite(v) and v > thr:
                    alerts.append((s, name, float(v), float(thr)))
            if missing[s] > self.max_missing:
                alerts.append((s, "missing", missing[s], self.max_missing))
        report = DriftReport(self._index, len(frame), int(bad.sum()), missing, stats, alerts)
        self._index += 1
        return report

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

    With m sensors each tested at level target_far / m (Bonferroni), the window-level false-alarm rate
    is at most about target_far. The threshold is the (1 - target_far / m) quantile of the statistic
    over all stable windows ("higher" interpolation: never below an observed value).
    """
    if stat not in STATS:
        raise ValueError(f"unknown statistic {stat!r}")
    sensors = tuple(sensors)
    probe = DriftMonitor(reference, sensors, window, thresholds={}, bins=bins)
    values: dict[str, list[float]] = {s: [] for s in sensors}
    for w in stable_windows(stable_runs, window):
        rep = probe.window_stats(w)
        for s in sensors:
            v = rep.stats[s][stat]
            if np.isfinite(v):
                values[s].append(v)
    if not all(values.values()):
        raise ValueError("no complete stable windows to calibrate on")
    level = 1.0 - target_far / len(sensors)
    return {s: {stat: float(np.quantile(values[s], level, method="higher"))} for s in sensors}


def alarm_rate(reports) -> float:
    """Share of reports with at least one distribution alert (schema and missingness excluded)."""
    reports = list(reports)
    return float(np.mean([r.drift_alert for r in reports])) if reports else float("nan")
