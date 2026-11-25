"""Build the shipped detector's configuration from DEVELOPMENT data (SNAPSHOT of the w5d1 script).

    python project/get_skab.py                                    # once, from the repository root
    python labs/w5d1_inference_pipeline/lab/build_model.py     # a few seconds
    python labs/w5d1_inference_pipeline/lab/build_model.py --check   # rebuild and compare

Given complete. It works once you have implemented flowguard.inference.

The model is the one chosen in w4d5: flow-rate |z| with a 100-row burn-in, and the operating point
chosen on the 27 development experiments of the frozen manifest v2 for an alert budget of one false
alarm per 8 hours, on the same grid as w4d5. Note that the development scores come from
``Detector.score_batch``: the object that will serve is the object whose operating point is chosen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import load_raw  # noqa: E402
from flowguard.inference import Detector, serving_frame  # noqa: E402
from flowguard.operating import choose_operating_point  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402

BURN_IN = 100
BUDGET = 1 / 8
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
MANIFEST = HERE / "splits" / "v2.json"
OUT = HERE / "model" / "model.json"


def build(raw_dir: Path) -> dict:
    tidy = load_raw(raw_dir)
    manifest = load_splits(MANIFEST)
    validate_splits(manifest, tidy)
    dev_ids = dev_experiments(manifest)
    dev = tidy[tidy["experiment_id"].isin(dev_ids)].reset_index(drop=True)

    detector = Detector(name="flowguard-flowrate", version="1.0.0", sensor="flow_rate", n_burn=BURN_IN)
    frame, errors = detector.score_batch(serving_frame(dev))
    if errors:
        raise RuntimeError(f"development runs could not be scored: {errors}")
    scores = frame["score"].to_numpy()
    scored = dev["t"].to_numpy() >= BURN_IN
    grid = np.unique(np.quantile(scores[scored], np.linspace(0.5, 0.999, 30)))
    point = choose_operating_point(dev, scores, BUDGET, grid, min_durations=(1, 5, 10, 30),
                                   merge_gaps=(0, 10, 60), burn_in=BURN_IN)
    detector.threshold = point["threshold"]
    detector.min_duration, detector.merge_gap = point["min_duration"], point["merge_gap"]
    ev = point["dev"]
    detector.metadata = {
        "chosen_in": "w4d5_model_choice (decision memo)",
        "trained_on": {"manifest": "splits/v2.json", "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                       "development_experiments": len(dev_ids)},
        "operating_point": {"alert_budget_per_hour": BUDGET, "feasible_on_dev": bool(point["feasible"]),
                            "dev_events_detected": f"{ev['n_detected']}/{ev['n_events']}",
                            "dev_false_alarms_per_hour": ev["false_alarms_per_hour"]},
    }
    return detector.to_config()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--check", action="store_true", help="rebuild and compare with model/model.json")
    args = ap.parse_args(argv)
    try:
        config = build(Path(args.raw_dir))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(config, indent=2, sort_keys=True) + "\n"
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print("model/model.json is reproducible" if same else "model/model.json DIFFERS from a rebuild")
        return 0 if same else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT}: threshold {config['threshold']:.4f}, min_duration {config['min_duration']}, "
          f"merge_gap {config['merge_gap']}; dev events {config['metadata']['operating_point']['dev_events_detected']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
