"""Train the logistic candidate on the REAL development data, bundle it with YOUR logistic_bundle.py,
register it, load it back and check it scores the test experiments exactly like the trained object.

    python project/get_skab.py                                              # once
    python labs/w5d2_artifacts_versioning/challenge/publish_logistic.py  # about 20 seconds

Given complete. Needs logistic_bundle.py and src/flowguard/artifacts.py (copied from your lab).
It starts from an empty challenge/results/ each run (a demo convenience; a real registry is never wiped).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "src")]

from logistic_bundle import load_logistic, save_logistic  # noqa: E402

from flowguard.artifacts import promote, register, resolve  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.detectors import SupervisedLogistic  # noqa: E402
from flowguard.metrics import pr_auc  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
N_BURN = 100


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--registry", default=str(HERE / "results" / "registry"))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(HERE / "splits" / "v2.json")
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))]
    test = tidy[tidy["experiment_id"].isin(manifest["test"])]
    model = SupervisedLogistic(n_burn=N_BURN).fit(dev)
    metadata = {
        "intended_use": "Educational prototype; shadow scorer next to flowguard-flowrate, not used for alarms.",
        "limitations": ["Trained on 27 laboratory runs with labelled faults; may not transfer to unseen fault families."],
        "training_data": {"manifest": "splits/v2.json", "development_experiments": int(dev["experiment_id"].nunique())},
        "evaluation": {"see": "w4d5 decision memo; development PR-AUC 0.834 [0.762, 0.895]"},
        "code_version": "see the repository commit",
    }
    out = HERE / "results"
    if out.exists():
        shutil.rmtree(out)
    staging = out / "bundle"
    save_logistic(model, staging, metadata, version="0.1.0")
    dest = register(args.registry, staging)
    promote(args.registry, "flowguard-logistic", "0.1.0")
    loaded = load_logistic(resolve(args.registry, "flowguard-logistic"))

    diffs, ys, ss = [], [], []
    for _, run in test.groupby("experiment_id", sort=False):
        run = run.sort_values("t")
        trained = model.calibrate(run.iloc[:N_BURN]).score(run.iloc[N_BURN:])
        served = loaded.score_run(run)
        diffs.append(np.abs(trained - served).max())
        ys.append(run["anomaly"].to_numpy()[N_BURN:])
        ss.append(served)
    print(f"registered at {dest}; files {sorted(p.name for p in dest.iterdir())}, "
          f"{sum(p.stat().st_size for p in dest.iterdir())} bytes in total")
    print(f"max |loaded - trained| over the 7 test runs: {max(diffs):.3g}")
    print(f"test PR-AUC from the loaded bundle: {pr_auc(np.concatenate(ys), np.concatenate(ss)):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
