"""How much worse is degraded mode? Model vs fallback rule on the 7 TEST experiments (frozen v2 manifest).

    python scripts/compare_fallback.py [--raw ...] [--json out.json]

Both alarm streams get the same post-processing as the shipped operating point (merge gaps of up to
merge_gap rows, keep runs of at least min_duration rows) and are scored after each experiment's burn-in.
Reported: faults detected (an alarm event overlapping the labelled segment), false alarm events per hour
of normal operation, and point precision/recall of the raw alarm rows.
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.guards import fallback_alarms  # noqa: E402
from flowguard.splits import load_splits  # noqa: E402


def default_raw() -> str:
    """data/raw/skab of the repository this lab lives in (works for lessons/ and solutions/ copies)."""
    for parent in HERE.parents:
        if (parent / "data" / "raw" / "skab").is_dir():
            return str(parent / "data" / "raw" / "skab")
    return "data/raw/skab"


def events(flags: np.ndarray, min_duration: int, merge_gap: int) -> list[tuple[int, int]]:
    """Runs of True (inclusive start, exclusive end) after merging gaps <= merge_gap; keep len >= min_duration."""
    runs, start = [], None
    for i, f in enumerate(np.append(flags, False)):
        if f and start is None:
            start = i
        elif not f and start is not None:
            runs.append([start, i])
            start = None
    merged: list[list[int]] = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= merge_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a, b) for a, b in merged if b - a >= min_duration]


def assess(flags, y, seconds, min_duration, merge_gap) -> dict:
    ev = events(flags, min_duration, merge_gap)
    fault = np.flatnonzero(y)
    detected = bool(fault.size) and any(a <= fault[-1] and b > fault[0] for a, b in ev)
    false_events = sum(1 for a, b in ev if not y[a:b].any())
    tp = int(np.sum(flags & (y == 1)))
    return {"detected": detected, "false_events": false_events, "flagged": int(flags.sum()), "tp": tp,
            "positives": int(y.sum()), "normal_hours": float(seconds[y == 0].sum() / 3600)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", default=default_raw())
    ap.add_argument("--json")
    args = ap.parse_args()
    model = load_bundle(HERE / "bundle")
    service = tomllib.loads((HERE / "configs" / "service.toml").read_text())
    test = load_splits(HERE / "splits" / "v2.json")["test"]
    tidy = load_raw(args.raw)
    totals = {name: {"detected": 0, "false_events": 0, "flagged": 0, "tp": 0, "positives": 0, "normal_hours": 0.0}
              for name in ("model", "fallback")}
    per_exp = []
    for eid in test:
        g = tidy[tidy["experiment_id"] == eid].sort_values("t")
        x = g[model.sensor].to_numpy(dtype=float)
        dt = g["datetime"].diff().dt.total_seconds().fillna(1.0).clip(upper=5.0).to_numpy()
        keep = slice(model.n_burn_in, None)
        y = g["anomaly"].to_numpy(dtype=int)[keep]
        flags = {"model": model.above_threshold(model.score(x[: model.n_burn_in], x))[keep],
                 "fallback": np.array(fallback_alarms(x, service["envelope_low"], service["envelope_high"]))[keep]}
        row = {"experiment_id": eid}
        for name, f in flags.items():
            r = assess(np.asarray(f, dtype=bool), y, dt[keep], model.min_duration, model.merge_gap)
            row[name] = r
            for k in totals[name]:
                totals[name][k] += r[k]
        per_exp.append(row)
    summary = {}
    for name, t in totals.items():
        summary[name] = {"faults_detected": int(t["detected"]), "faults": len(test),
                         "false_alarms_per_hour": t["false_events"] / t["normal_hours"],
                         "precision": t["tp"] / max(t["flagged"], 1), "recall": t["tp"] / max(t["positives"], 1),
                         "normal_hours": t["normal_hours"]}
        print(f"{name:9s} faults {t['detected']}/{len(test)}  false alarms/h {summary[name]['false_alarms_per_hour']:.2f}"
              f"  point precision {summary[name]['precision']:.3f} recall {summary[name]['recall']:.3f}")
    for row in per_exp:
        print(f"  {row['experiment_id']:10s} model {'hit ' if row['model']['detected'] else 'miss'}"
              f"  fallback {'hit ' if row['fallback']['detected'] else 'miss'}")
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": summary, "per_experiment": per_exp}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
