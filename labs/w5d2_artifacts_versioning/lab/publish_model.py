"""Build, bundle, register and promote the shipped detector, on the REAL development data.

    python project/get_skab.py                                         # once, from the repository root
    python labs/w5d2_artifacts_versioning/lab/publish_model.py      # about 30 seconds

Given complete. It works once you have implemented flowguard.artifacts.

1. Build the flow-rate detector exactly as in w5d1 (operating point from development data).
2. Measure what the model card reports: development PR-AUC with a cluster-bootstrap interval and
   the single test look at the frozen operating point.
3. save_bundle -> register as flowguard-flowrate 1.0.0 -> promote -> resolve("current") -> load_bundle.
4. Prove the loaded detector is the built one: identical scores on the 7 test experiments.
The registry is written to lab/results/registry (git-ignored); --registry chooses another place.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from build_model import BURN_IN, MANIFEST, build  # noqa: E402

from flowguard.artifacts import load_bundle, promote, register, resolve, save_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.inference import Detector, serving_frame  # noqa: E402
from flowguard.metrics import pr_auc  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402
from flowguard.uncertainty import cluster_bootstrap, wilson_interval  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)


def code_version() -> str:
    try:
        out = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain", "--", "."],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return out.stdout.strip() + ("+uncommitted-changes" if dirty else "") if out.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def pooled(results):
    y = np.concatenate([r[0] for r in results])
    s = np.concatenate([r[1] for r in results])
    return pr_auc(y, s)


def per_cluster(frame, scores, manifest):
    cluster = {e: e for e in frame["experiment_id"].unique()}
    for group in manifest.get("overlap_groups", []):
        members = sorted(set(group) & set(cluster))
        for e in members:
            cluster[e] = "+".join(members)
    keep = frame["t"].to_numpy() >= BURN_IN
    f = frame[keep].assign(_s=scores[keep], _c=frame.loc[keep, "experiment_id"].map(cluster))
    return {c: (g["anomaly"].to_numpy(), g["_s"].to_numpy()) for c, g in f.groupby("_c")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--registry", default=str(HERE / "results" / "registry"))
    ap.add_argument("--fresh", action="store_true", help="delete the registry first (a demo convenience)")
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    detector = Detector.from_config(build(Path(args.raw_dir)))
    manifest = load_splits(MANIFEST)
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))].reset_index(drop=True)
    test = tidy[tidy["experiment_id"].isin(manifest["test"])].reset_index(drop=True)

    dev_scores = detector.score_batch(serving_frame(dev))[0]["score"].to_numpy()
    clusters = per_cluster(dev, dev_scores, manifest)
    ci = cluster_bootstrap(pooled, clusters, n_boot=2000, seed=0)
    test_scores = detector.score_batch(serving_frame(test))[0]["score"].to_numpy()
    keep = test["t"].to_numpy() >= BURN_IN
    ev = evaluate_experiments(test, np.nan_to_num(test_scores, nan=-np.inf) >= detector.threshold, burn_in=BURN_IN,
                              min_duration=detector.min_duration, merge_gap=detector.merge_gap)
    lo, hi = wilson_interval(ev["n_detected"], ev["n_events"])

    burn = dev[dev["t"] < BURN_IN].groupby("experiment_id")["flow_rate"]
    reference = {"burn_in_mean": burn.mean().to_numpy(), "burn_in_std": burn.std(ddof=0).to_numpy()}
    metadata = {
        "intended_use": ("Educational prototype: alarm when the SKAB laboratory water-circulation loop leaves "
                         "normal operation, one run at a time, after a 100-row start-up calibration."),
        "limitations": [
            "Validated on 7 test runs from one laboratory testbed; no claim about any real plant.",
            "Sees only faults that move flow rate away from its start-up level.",
            "Assumes the first 100 rows of a run are normal; a run that starts faulty becomes its own baseline.",
            "At the 1-per-8-h alert budget it detected 5 of 7 test faults; silence is not proof of health.",
        ],
        "training_data": {"source": "SKAB v0.9 (GPL-3.0), see project/README.md", "manifest": "splits/v2.json",
                          "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                          "development_experiments": int(dev["experiment_id"].nunique())},
        "evaluation": {
            "development": {"pr_auc": round(ci["estimate"], 4), "pr_auc_95ci": [round(ci["low"], 4), round(ci["high"], 4)],
                            "resampling_unit": "overlap cluster", "clusters": len(clusters)},
            "test_single_look": {"pr_auc": round(pr_auc(test["anomaly"].to_numpy()[keep], test_scores[keep]), 4),
                                 "events_detected": f"{ev['n_detected']}/{ev['n_events']}",
                                 "event_recall_wilson_95ci": [round(lo, 2), round(hi, 2)],
                                 "false_alarms_per_hour": round(ev["false_alarms_per_hour"], 3)},
        },
        "code_version": code_version(),
    }

    registry = Path(args.registry)
    if args.fresh and registry.exists():
        shutil.rmtree(registry)
    staging = HERE / "results" / "bundle-staging"
    if staging.exists():
        shutil.rmtree(staging)
    save_bundle(detector, staging, metadata, reference)
    path = register(registry, staging)
    promote(registry, detector.name, detector.version)
    current = resolve(registry, detector.name)
    loaded, card, ref = load_bundle(current)
    again = loaded.score_batch(serving_frame(test))[0]["score"].to_numpy()

    print(f"registered {detector.name} {detector.version} at {path}")
    print(f"current -> {current.name}; files: {sorted(p.name for p in current.iterdir())}")
    print(f"sizes (bytes): " + ", ".join(f"{p.name} {p.stat().st_size}" for p in sorted(current.iterdir())))
    print(f"loaded == built: config {loaded.to_config() == detector.to_config()}, "
          f"max |score difference| on test {np.nanmax(np.abs(again - test_scores)):.3g}, "
          f"reference arrays {sorted(ref)} of length {len(ref['burn_in_mean'])}")
    print("model card:")
    print(json.dumps({k: card[k] for k in ("name", "version", "evaluation", "code_version")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
