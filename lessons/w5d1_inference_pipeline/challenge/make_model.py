"""Train the logistic candidate on the REAL development experiments and write model/logistic.json.

    python project/get_skab.py                                         # once
    python lessons/w5d1_inference_pipeline/challenge/make_model.py     # about 10 seconds
    python lessons/w5d1_inference_pipeline/challenge/make_model.py --check

Given complete; the JSON it writes is committed, so the challenge and its checks do not need the data.
The training path is flowguard.detectors.SupervisedLogistic (the w4d5 snapshot in ../lab/src).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lab" / "src"))

import sklearn  # noqa: E402

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.detectors import Z_CLIP, SupervisedLogistic  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
OUT = HERE / "model" / "logistic.json"
N_BURN = 100


def build(raw_dir: Path) -> dict:
    tidy = load_raw(raw_dir)
    manifest = load_splits(HERE.parent / "lab" / "splits" / "v2.json")
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))]
    model = SupervisedLogistic(n_burn=N_BURN).fit(dev).model_
    return {
        "name": "flowguard-logistic", "version": "0.1.0", "n_burn": N_BURN, "z_clip": Z_CLIP,
        "sensors": list(SENSOR_COLUMNS),
        "features": [f"z:{s}" for s in SENSOR_COLUMNS] + [f"abs_z:{s}" for s in SENSOR_COLUMNS],
        "coef": [float(c) for c in model.coef_.ravel()], "intercept": float(model.intercept_[0]),
        "trained_with": {"scikit-learn": sklearn.__version__, "C": 1.0, "manifest": "splits/v2.json"},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    text = json.dumps(build(Path(args.raw_dir)), indent=2) + "\n"
    if args.check:
        same = OUT.read_text() == text
        print("model/logistic.json is reproducible" if same else "model/logistic.json DIFFERS")
        return 0 if same else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
