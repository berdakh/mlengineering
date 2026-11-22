"""Scheduled evaluation: score the frozen test experiments with the shipped bundle and write a report.

    python scripts/fetch_skab.py                       # once (about 4 MB)
    python scripts/evaluate.py --out reports/evaluation.json [--min-events 4]

This is the SLOW lane (lesson w6d3, section 2.5): it needs downloaded data and its result is a
statistical estimate on 7 experiments, so it runs on a schedule or on demand, never as a per-push gate.
``--min-events`` turns it into an alert: exit 1 if fewer test faults are detected than the floor.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402


def average_precision(y: np.ndarray, s: np.ndarray) -> float:
    """Step-wise average precision (same definition as scikit-learn's average_precision_score)."""
    order = np.argsort(-s, kind="mergesort")
    y, s = y[order], s[order]
    distinct = np.r_[np.diff(s) != 0, True]
    tp = np.cumsum(y)[distinct]
    fp = np.cumsum(1 - y)[distinct]
    precision = tp / (tp + fp)
    recall = tp / y.sum()
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--model-dir", default=str(ROOT / "models" / "flowguard-z" / "1.0.0"))
    ap.add_argument("--manifest", default=str(ROOT / "splits" / "v2.json"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "evaluation.json"))
    ap.add_argument("--min-events", type=int, default=None)
    args = ap.parse_args(argv)
    detector, info = load_bundle(args.model_dir)
    manifest = json.loads(Path(args.manifest).read_text())
    tidy = load_raw(args.raw_dir)
    ys, ss, per_experiment = [], [], []
    for exp_id in sorted(manifest["test"]):
        run = tidy[tidy["experiment_id"] == exp_id].sort_values("t")
        scores = detector.score_batch(run)
        valid = ~np.isnan(scores)
        y = run["anomaly"].to_numpy()[valid]
        s = scores[valid]
        flagged = s >= detector.threshold
        detected = bool(flagged[y == 1].any())
        per_experiment.append({"experiment_id": exp_id, "detected": detected,
                               "flagged_normal_samples": int(flagged[y == 0].sum()),
                               "normal_samples": int((y == 0).sum())})
        ys.append(y)
        ss.append(s)
    y_all, s_all = np.concatenate(ys), np.concatenate(ss)
    n_detected = sum(e["detected"] for e in per_experiment)
    report = {
        "model_version": detector.version,
        "manifest": Path(args.manifest).name,
        "n_test_experiments": len(per_experiment),
        "point_average_precision": round(average_precision(y_all, s_all), 4),
        "prevalence": round(float(y_all.mean()), 4),
        "events_detected": n_detected,
        "per_experiment": per_experiment,
        "note": "raw exceedances of the threshold; no min_duration/merge post-processing; no intervals",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['model_version']}: AP {report['point_average_precision']} "
          f"(prevalence {report['prevalence']}), {n_detected}/{len(per_experiment)} test faults hit -> {out}")
    if args.min_events is not None and n_detected < args.min_events:
        print(f"ALERT: {n_detected} detected < floor {args.min_events}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
