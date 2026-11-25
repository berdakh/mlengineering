"""Build three model bundles from DEVELOPMENT data of the frozen manifest v2. Given complete.

    python project/get_skab.py                                                # once
    python labs/w7d4_model_updates_rollback/lab/build_models.py            # about 1-2 minutes

Writes ``results/bundles/<name>-<version>/`` (no pickle; JSON + checksums):

* ``1.0.0`` the shipped model (w4d5): flow-rate |z|, alert budget 1 false alarm per 8 hours.
* ``1.1.0`` the same detector re-tuned after the reliability engineer accepted a budget of 1 false
  alarm per hour (a stakeholder decision, stated in the bundle's metadata).
* ``2.0.0`` max |z| over flow rate and both accelerometers, budget 1 per 8 hours. It needs two
  columns the plant gateway does not send today.

Operating points come from ``flowguard.operating.choose_operating_point`` on the 27 development
experiments, the same grid as w4d5. The test experiments are not touched here.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import load_raw  # noqa: E402
from flowguard.models import BurnInZ, score_experiments  # noqa: E402
from flowguard.operating import choose_operating_point  # noqa: E402
from flowguard.registry import save_bundle  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
MANIFEST = HERE / "splits" / "v2.json"
SPECS = [
    ("1.0.0", ("flowguard",), ("flow_rate",), 1 / 8, "shipped in w4d5: alert budget 1 per 8 h"),
    ("1.1.0", ("flowguard",), ("flow_rate",), 1.0, "re-tuned: stakeholder accepted 1 false alarm per hour"),
    ("2.0.0", ("flowguard",), ("flow_rate", "accelerometer1_rms", "accelerometer2_rms"), 1 / 8,
     "adds both accelerometers: alert budget 1 per 8 h"),
]


def build(raw_dir: Path, out_dir: Path) -> list[Path]:
    tidy = load_raw(raw_dir)
    manifest = load_splits(MANIFEST)
    validate_splits(manifest, tidy)
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))].reset_index(drop=True)
    paths = []
    for version, (name,), sensors, budget, why in SPECS:
        base = BurnInZ(name=name, version=version, sensors=sensors)
        scores = score_experiments(base, dev)
        grid = np.unique(np.quantile(scores[np.isfinite(scores)], np.linspace(0.5, 0.999, 30)))
        point = choose_operating_point(dev, np.nan_to_num(scores, nan=-1.0), budget, grid,
                                       min_durations=(1, 5, 10, 30), merge_gaps=(0, 10, 60), burn_in=base.n_burn)
        model = BurnInZ(name=name, version=version, sensors=sensors, threshold=point["threshold"],
                        min_duration=point["min_duration"], merge_gap=point["merge_gap"])
        ev = point["dev"]
        meta = {"why": why, "alert_budget_per_hour": budget, "feasible_on_dev": bool(point["feasible"]),
                "dev_events_detected": f"{ev['n_detected']}/{ev['n_events']}",
                "dev_false_alarms": int(ev["n_false_alarms"]), "dev_normal_hours": round(ev["normal_hours"], 3),
                "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
        paths.append(save_bundle(model, out_dir / f"{name}-{version}", meta))
        print(f"{name} {version}: sensors {list(sensors)}, threshold {model.threshold:.4f}, "
              f"min_duration {model.min_duration}, merge_gap {model.merge_gap}; dev {meta['dev_events_detected']} "
              f"events, {meta['dev_false_alarms']} false alarms in {meta['dev_normal_hours']} h")
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--out", default=str(HERE / "results" / "bundles"))
    args = ap.parse_args(argv)
    if not Path(args.raw_dir).is_dir():
        print(f"error: {args.raw_dir} not found; run python project/get_skab.py first", file=sys.stderr)
        return 2
    build(Path(args.raw_dir), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
