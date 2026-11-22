"""Event-level effect of streaming alarm hysteresis on DEVELOPMENT experiments (reference solution).

    python solutions/lessons/w5d3_online_inference/challenge/evaluate_hysteresis.py   # about 20 s

The test set is not read: this compares alarm rules, which is a design choice.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(HERE / "src"))

from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.hysteresis import hysteresis_batch  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402

GRID_K = (1, 5, 10, 30)
GRID_M = (1, 10, 60)


def fmt_delay(d: float) -> str:
    return "missed" if not np.isfinite(d) else f"{d:.0f} s"


def main() -> int:
    tidy = load_raw(REPO_ROOT / "data" / "raw" / "skab")
    detector, _ = load_bundle(HERE / "models" / "flowguard-z" / "1.0.0")
    manifest = load_splits(HERE / "splits" / "v2.json")
    validate_splits(manifest, tidy)
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))].reset_index(drop=True)
    scores = np.full(len(dev), np.nan)
    for _, g in dev.groupby("experiment_id", sort=False):
        scores[g.index.to_numpy()] = detector.score_batch(g.sort_values("t"))
    exceeds = np.where(np.isnan(scores), np.nan, scores >= detector.threshold)

    rows = []
    batch_rule = evaluate_experiments(dev, np.nan_to_num(exceeds, nan=0.0), burn_in=detector.n_burn,
                                      min_duration=detector.min_duration, merge_gap=detector.merge_gap)
    rows.append((f"batch post-processing (min_duration {detector.min_duration}, merge_gap {detector.merge_gap})",
                 batch_rule))
    for k in GRID_K:
        for m in GRID_M:
            flagged = np.zeros(len(dev), dtype=int)
            for _, g in dev.groupby("experiment_id", sort=False):
                idx = g.sort_values("t").index.to_numpy()
                flagged[idx] = hysteresis_batch(exceeds[idx], k, m)
            rows.append((f"stream hysteresis k={k:>2}, m={m:>2}",
                         evaluate_experiments(dev, flagged, burn_in=detector.n_burn)))

    print(f"development experiments: {dev['experiment_id'].nunique()}; threshold {detector.threshold:.4f}; "
          f"burn-in {detector.n_burn}")
    print("delay columns: over the DETECTED events only (missed events are counted in 'events')")
    print(f"{'rule':<52}{'events':>8}{'alarms':>8}{'false/h':>9}{'median delay':>14}{'max delay':>11}")
    for name, r in rows:
        found = np.array([d for d in r["delays_s"] if np.isfinite(d)])
        med = float(np.median(found)) if found.size else float("inf")
        worst = float(found.max()) if found.size else float("inf")
        print(f"{name:<52}{r['n_detected']:>4}/{r['n_events']:<3}{r['n_alarms']:>8}{r['false_alarms_per_hour']:>9.2f}"
              f"{fmt_delay(med):>14}{fmt_delay(worst):>11}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
