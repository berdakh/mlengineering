"""Rebuild the shipped model bundle from real SKAB data (given; you do not need to edit it).

    python <lab>/scripts/build_bundle.py --out /tmp/fg-bundle     # about 10 s; needs project/get_skab.py

The committed ``models/flowguard-z/1.0.0`` was produced by labs/w5d3_online_inference/lab/build_bundle.py.
This copy re-runs the same choice and writes the same detector parameters; only the ``built_by``
provenance field differs. Training-side code (this script, ``operating.py``, ``evaluation.py``) needs
scipy; the serving image does not, which is why scipy is in requirements-dev.txt only.

Re-runs the w4d5 operating-point choice for the flow-rate |z| detector on the DEVELOPMENT
experiments of the frozen manifest (splits/v2.json; the test set is not read) and writes
``models/flowguard-z/1.0.0/`` (or ``--out``).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]   # the lab root (this file is in scripts/)
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
sys.path.insert(0, str(HERE / "src"))

from flowguard.bundle import save_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.inference import Detector  # noqa: E402
from flowguard.operating import choose_operating_point  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402

N_BURN = 100
BUDGET_PER_HOUR = 1 / 8


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--out", default=str(HERE / "models" / "flowguard-z" / "1.0.0"))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest_path = HERE / "splits" / "v2.json"
    manifest = load_splits(manifest_path)
    validate_splits(manifest, tidy)
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))].reset_index(drop=True)

    probe = Detector(n_burn=N_BURN)
    scores = np.full(len(dev), np.nan)
    for _, g in dev.groupby("experiment_id", sort=False):
        scores[g.index.to_numpy()] = probe.score_batch(g)
    scored = dev["t"].to_numpy() >= N_BURN
    grid = np.unique(np.quantile(scores[scored], np.linspace(0.5, 0.999, 30)))
    point = choose_operating_point(dev, np.nan_to_num(scores, nan=0.0), BUDGET_PER_HOUR, grid,
                                   min_durations=(1, 5, 10, 30), merge_gaps=(0, 10, 60), burn_in=N_BURN)
    detector = Detector(n_burn=N_BURN, threshold=point["threshold"], min_duration=point["min_duration"],
                        merge_gap=point["merge_gap"], version="flowguard-z-1.0.0")
    provenance = {
        "chosen_in": "w4d5_model_choice", "built_by": "scripts/build_bundle.py (w6 lab copy)",
        "split_manifest": "splits/v2.json",
        "split_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "alert_budget_per_hour": BUDGET_PER_HOUR,
        "dev_event_recall": point["dev"]["event_recall"],
        "dev_events": f"{point['dev']['n_detected']}/{point['dev']['n_events']}",
        "dev_false_alarms_per_hour": point["dev"]["false_alarms_per_hour"],
        "budget_met_on_dev": bool(point["feasible"]),
    }
    out = save_bundle(detector, args.out, provenance)
    print(f"threshold {detector.threshold:.4f}, min_duration {detector.min_duration}, merge_gap {detector.merge_gap}")
    print(f"dev: events {provenance['dev_events']}, false alarms/h {provenance['dev_false_alarms_per_hour']:.2f}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
