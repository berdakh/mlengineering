"""Data-quality checks for the tidy SKAB table.

``run_checks`` never raises on bad data: it returns one ``CheckResult`` per check.
Deciding what to do about a failure (stop, warn, continue) belongs to the caller.

Severity
    ``error``    the table violates the contract every later step relies on; stop.
    ``warning``  the data is valid as recorded but a modelling decision depends on it; record and continue.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from flowguard.data import LABEL_COLUMNS, SENSOR_COLUMNS, TIDY_COLUMNS

MAX_GAP_SECONDS = 5.0       # nominal sampling interval is 1 s
STUCK_RUN_SAMPLES = 120     # longest run of identical values seen in the real data is 43 (flow_rate)
MIN_ROWS = 100
# Generous physical plausibility limits, not statistical outlier limits.
RANGES = {
    "accelerometer1_rms": (0.0, 5.0), "accelerometer2_rms": (0.0, 5.0), "current": (0.0, 10.0),
    "pressure": (-2.0, 5.0), "temperature": (0.0, 150.0), "thermocouple": (0.0, 100.0),
    "voltage": (150.0, 300.0), "flow_rate": (0.0, 300.0),
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    severity: str = "error"

    def to_dict(self) -> dict:
        return asdict(self)


def _fmt(items, limit: int = 8) -> str:
    items = [str(i) for i in items]
    extra = f" (+{len(items) - limit} more)" if len(items) > limit else ""
    return ", ".join(items[:limit]) + extra


def _result(name: str, offenders: dict, severity: str, ok: str) -> CheckResult:
    """``offenders`` maps experiment_id -> short description of what is wrong there."""
    if not offenders:
        return CheckResult(name, True, ok, severity)
    detail = "; ".join(f"{exp}: {msg}" for exp, msg in list(offenders.items())[:12])
    if len(offenders) > 12:
        detail += f"; (+{len(offenders) - 12} more experiments)"
    return CheckResult(name, False, detail, severity)


def _longest_run(values: np.ndarray) -> int:
    if len(values) == 0:
        return 0
    starts = np.flatnonzero(np.r_[True, values[1:] != values[:-1]])
    return int(np.diff(np.r_[starts, len(values)]).max())


def _n_segments(binary: np.ndarray) -> int:
    return int((np.diff(np.r_[0, binary]) == 1).sum())


def run_checks(tidy: pd.DataFrame) -> list[CheckResult]:
    missing = [c for c in TIDY_COLUMNS if c not in tidy.columns]
    if missing:
        # Nothing else can be evaluated meaningfully without the full schema.
        return [CheckResult("required_columns", False, f"missing column(s): {_fmt(missing)}", "error")]
    results = [CheckResult("required_columns", True, f"{len(TIDY_COLUMNS)} columns present", "error")]
    groups = dict(tuple(tidy.groupby("experiment_id", sort=True)))

    # --- errors: contract violations -------------------------------------------------
    bad = {}
    for exp, g in groups.items():
        counts = {c: int(g[c].isna().sum()) for c in ("datetime", *SENSOR_COLUMNS, *LABEL_COLUMNS)}
        counts = {c: n for c, n in counts.items() if n}
        if counts:
            bad[exp] = "missing or unparseable values " + str(counts)
    results.append(_result("no_missing_values", bad, "error", "no missing or unparseable values"))

    bad = {}
    for exp, g in groups.items():
        for col in LABEL_COLUMNS:
            odd = sorted(set(pd.unique(g[col].dropna())) - {0, 1})
            if odd:
                bad[exp] = f"{col} has values outside {{0, 1}}: {_fmt(odd)}"
    results.append(_result("labels_binary", bad, "error", "labels are 0/1"))

    bad = {}
    for exp, g in groups.items():
        dup = g["datetime"].dropna().duplicated(keep=False)
        if dup.any():
            stamps = g["datetime"].dropna()[dup].drop_duplicates()
            bad[exp] = f"{int(dup.sum())} rows share {len(stamps)} timestamp(s), e.g. {stamps.iloc[0]}"
    results.append(_result("unique_timestamps", bad, "error", "(experiment_id, datetime) is unique"))

    bad = {}
    for exp, g in groups.items():
        step = g["datetime"].diff().dt.total_seconds().to_numpy()[1:]
        backwards = int(np.sum(step < 0))
        if backwards:
            bad[exp] = f"time goes backwards at {backwards} row(s); rows are not in time order"
    results.append(_result("time_ordered", bad, "error", "rows are in non-decreasing time order"))

    bad = {}
    for exp, g in groups.items():
        if exp.startswith("anomaly-free/"):
            n = int(pd.to_numeric(g["anomaly"], errors="coerce").fillna(0).sum())
            if n:
                bad[exp] = f"{n} anomalous samples in a recording declared anomaly-free"
    results.append(_result("anomaly_free_is_clean", bad, "error", "anomaly-free recordings have no positive labels"))

    # --- warnings: valid data that constrains modelling ----------------------------------
    bad = {}
    step = tidy["datetime"].diff().dt.total_seconds()          # diff over the whole table
    for idx in step[step > MAX_GAP_SECONDS].index:
        exp = tidy.loc[idx, "experiment_id"]
        bad[exp] = f"gap of {step[idx]:g} s at t={int(tidy.loc[idx, 't'])}"
    results.append(_result("sampling_gaps", bad, "warning", f"no sampling gap above {MAX_GAP_SECONDS:g} s"))

    bad = {}
    for exp, g in groups.items():
        stuck = {c: _longest_run(g[c].to_numpy()) for c in SENSOR_COLUMNS}
        stuck = {c: n for c, n in stuck.items() if n >= STUCK_RUN_SAMPLES}
        if stuck:
            bad[exp] = "constant for many consecutive samples " + str(stuck)
    results.append(_result("stuck_sensors", bad, "warning",
                           f"no sensor constant for {STUCK_RUN_SAMPLES}+ consecutive samples"))

    bad = {}
    for exp, g in groups.items():
        out = {}
        for col, (lo, hi) in RANGES.items():
            n = int(((g[col] < lo) | (g[col] > hi)).sum())
            if n:
                out[col] = f"{n} outside [{lo:g}, {hi:g}]"
        if out:
            bad[exp] = str(out)
    results.append(_result("plausible_ranges", bad, "warning", "all sensor values inside plausibility limits"))

    bad = {}
    for exp, g in groups.items():
        if exp.startswith("anomaly-free/"):
            continue
        labels = pd.to_numeric(g["anomaly"], errors="coerce").fillna(0).to_numpy()
        n = _n_segments((labels == 1).astype(int))
        if n != 1:
            bad[exp] = f"{n} anomalous segments (the evaluation design assumes exactly 1)"
    results.append(_result("one_anomaly_segment", bad, "warning", "each labelled experiment has exactly one anomalous segment"))

    bad = {exp: f"only {len(g)} rows" for exp, g in groups.items() if len(g) < MIN_ROWS}
    results.append(_result("enough_rows", bad, "warning", f"every experiment has at least {MIN_ROWS} rows"))
    return results


def summarise(results: list[CheckResult]) -> dict:
    failed = [r for r in results if not r.passed]
    return {
        "n_checks": len(results),
        "n_failed_errors": sum(r.severity == "error" for r in failed),
        "n_failed_warnings": sum(r.severity == "warning" for r in failed),
        "results": [r.to_dict() for r in results],
    }
