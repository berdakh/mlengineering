"""Classical detectors under one protocol on the REAL SKAB data.

    python project/get_skab.py                                          # once, from the repo root
    python lessons/w4d2_classical_detectors/lab/compare_detectors.py    # a few minutes on a laptop CPU

This file is complete. It works once you have implemented flowguard.detectors.

One protocol for every detector (the "fair comparison" of the lesson):
* the same 40 causal features (flowguard.windowfeatures: burn-in z of 8 sensors + rolling mean and SD
  over 10 and 30 rows), the same rows (t >= BURN_IN), the same frozen split (lab/splits/v2.json);
* the same tuning budget: 3 configurations per detector, chosen by out-of-fold PR-AUC over the 4
  development folds;
* the same threshold rule: best F1 on the out-of-fold development scores;
* semi-supervised detectors are fitted on the NORMAL rows (anomaly == 0) of the training folds; the
  supervised GBT on all rows of the training folds with their labels;
* test: point PR-AUC with a 95% cluster-bootstrap interval over the 7 test experiments, event recall,
  false alarms per hour, median delay.

Protocol B (development experiments only, the test set is not touched): train on the valve1 and valve2
development experiments, evaluate on the development experiments of the unseen family `other`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "splits" / "v2.json"
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import load_raw  # noqa: E402
from flowguard.detectors import GBTDetector, IForestDetector, PCADetector  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.metrics import best_f1_threshold, pr_auc  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402
from flowguard.uncertainty import cluster_bootstrap  # noqa: E402
from flowguard.windowfeatures import feature_columns, window_features  # noqa: E402

BURN_IN = 100
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"


class FlowZ:
    """The w2d6 baseline expressed on the same features: |burn-in z| of the flow rate. No fitting."""

    def fit(self, features, labels=None):
        return self

    def score(self, features):
        return np.abs(features["z_flow_rate"].to_numpy())


DETECTORS = {
    "flow_rate abs z (w2d6 baseline)": ("none", [lambda: FlowZ()]),
    "PCA T2": ("normal", [lambda v=v: PCADetector(variance=v, statistic="t2") for v in (0.8, 0.9, 0.95)]),
    "PCA Q (SPE)": ("normal", [lambda v=v: PCADetector(variance=v, statistic="q") for v in (0.8, 0.9, 0.95)]),
    "isolation forest": ("normal", [lambda m=m: IForestDetector(max_samples=m, seed=0) for m in (128, 256, 1024)]),
    "gradient-boosted trees": ("supervised", [
        lambda: GBTDetector(learning_rate=0.1, max_leaf_nodes=15, seed=0),
        lambda: GBTDetector(learning_rate=0.1, max_leaf_nodes=31, seed=0),
        lambda: GBTDetector(learning_rate=0.05, max_leaf_nodes=31, max_iter=300, seed=0)]),
}


def fit_score(make, mode, train, apply, cols):
    det = make()
    if mode == "normal":
        normal = train[train["anomaly"] == 0]
        det.fit(normal[cols])
    elif mode == "supervised":
        det.fit(train[cols], train["anomaly"].to_numpy())
    else:
        det.fit(train[cols])
    return det.score(apply[cols])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(MANIFEST)
    validate_splits(manifest, tidy)
    frame = window_features(tidy, n_burn=BURN_IN)
    frame = frame[frame["t"] >= BURN_IN]
    cols = feature_columns(frame)
    dev_ids, test_ids = dev_experiments(manifest), manifest["test"]
    dev = frame[frame["experiment_id"].isin(dev_ids)]
    test = frame[frame["experiment_id"].isin(test_ids)]
    print(f"features: {len(cols)}; development rows {len(dev)} ({len(dev_ids)} experiments), "
          f"test rows {len(test)} ({len(test_ids)} experiments)\n")

    results, table_b = [], []
    print("A. Frozen split. Config chosen by out-of-fold development PR-AUC; threshold = best out-of-fold F1.")
    print("| detector | chosen config (OOF dev PR-AUC) | test PR-AUC [95% CI] | events | false alarms / h | median delay (s) | fit+score s |")
    print("|---|---|---|---|---|---|---|")
    for name, (mode, makers) in DETECTORS.items():
        oof_by_cfg = []
        for make in makers:
            oof = np.zeros(len(dev))
            for fold in manifest["dev_folds"]:
                held = dev["experiment_id"].isin(fold).to_numpy()
                oof[held] = fit_score(make, mode, dev[~held], dev[held], cols)
            oof_by_cfg.append((pr_auc(dev["anomaly"].to_numpy(), oof), oof))
        best = int(np.argmax([c[0] for c in oof_by_cfg]))
        threshold, _ = best_f1_threshold(dev["anomaly"].to_numpy(), oof_by_cfg[best][1])
        start = time.perf_counter()
        s = fit_score(makers[best], mode, dev, test, cols)
        seconds = time.perf_counter() - start
        y = test["anomaly"].to_numpy()
        per_exp = {e: {"y": y[(test["experiment_id"] == e).to_numpy()], "s": s[(test["experiment_id"] == e).to_numpy()]}
                   for e in test_ids}
        ci = cluster_bootstrap(lambda rs: pr_auc(np.concatenate([r["y"] for r in rs]),
                                                 np.concatenate([r["s"] for r in rs])),
                               per_exp, n_boot=args.n_boot, seed=0)
        ev = evaluate_experiments(test, s >= threshold, burn_in=BURN_IN)
        cfg = makers[best]()
        cfg_txt = ", ".join(f"{k}={v}" for k, v in vars(cfg).items() if k != "seed") or "none"
        print(f"| {name} | {cfg_txt} ({oof_by_cfg[best][0]:.3f}) | {ci['estimate']:.3f} [{ci['low']:.3f}, {ci['high']:.3f}] | "
              f"{ev['n_detected']}/{ev['n_events']} | {ev['false_alarms_per_hour']:.1f} | {ev['median_delay_s']:.0f} | {seconds:.1f} |")
        results.append({"detector": name, "config": cfg_txt, "oof_dev_pr_auc": oof_by_cfg[best][0],
                        "pr_auc": ci["estimate"], "low": ci["low"], "high": ci["high"],
                        "detected": ev["n_detected"], "events": ev["n_events"],
                        "false_alarms_per_hour": ev["false_alarms_per_hour"], "median_delay_s": ev["median_delay_s"],
                        "seconds": seconds, "best_index": best})

    print("\nB. Leave-family-out on development experiments: train on valve1 + valve2, evaluate on `other`.")
    fam = dev["family"].to_numpy()
    train_b, eval_b = dev[fam != "other"], dev[fam == "other"]
    print(f"   train: {train_b['experiment_id'].nunique()} experiments; held-out family: "
          f"{eval_b['experiment_id'].nunique()} experiments; prevalence {eval_b['anomaly'].mean():.3f}")
    print("| detector | PR-AUC on unseen family [95% CI] | same detector, protocol A test |")
    print("|---|---|---|")
    for r, (name, (mode, makers)) in zip(results, DETECTORS.items()):
        s = fit_score(makers[r["best_index"]], mode, train_b, eval_b, cols)
        y = eval_b["anomaly"].to_numpy()
        ids = eval_b["experiment_id"].to_numpy()
        group_of = {e: "+".join(g) for g in manifest["overlap_groups"] for e in g}
        clusters = {}
        for e in np.unique(ids):
            c = clusters.setdefault(group_of.get(e, e), {"y": [], "s": []})
            c["y"].append(y[ids == e]); c["s"].append(s[ids == e])
        per = {k: {"y": np.concatenate(v["y"]), "s": np.concatenate(v["s"])} for k, v in clusters.items()}
        ci = cluster_bootstrap(lambda rs: pr_auc(np.concatenate([q["y"] for q in rs]),
                                                 np.concatenate([q["s"] for q in rs])), per, n_boot=args.n_boot, seed=0)
        print(f"| {name} | {ci['estimate']:.3f} [{ci['low']:.3f}, {ci['high']:.3f}] ({len(per)} clusters) | {r['pr_auc']:.3f} |")
        table_b.append({"detector": name, "pr_auc": ci["estimate"], "low": ci["low"], "high": ci["high"],
                        "n_clusters": len(per)})
    if args.json:
        Path(args.json).write_text(json.dumps({"A": results, "B": table_b}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
