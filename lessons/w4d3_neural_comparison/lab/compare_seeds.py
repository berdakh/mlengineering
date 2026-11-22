"""Neural autoencoder versus classical detectors on the REAL SKAB data, under one protocol.

    python project/get_skab.py                                           # once, from the repo root
    python lessons/w4d3_neural_comparison/lab/compare_seeds.py           # a few minutes on one CPU thread
    python lessons/w4d3_neural_comparison/lab/compare_seeds.py --quick   # 2 seeds, 1 config: about 2 minutes

This file is complete. It works once you have implemented flowguard.neural.

Protocol (the same for every detector):
* split: the frozen v2 manifest from w3d1 (lab/splits/v2.json): 7 test experiments, 27 development
  experiments in 4 folds. Folds 0-2 are FIT, fold 3 is VAL. The test set is read once, at the end.
* rows scored: t >= 100 (the burn-in rows of each experiment are used for calibration, not scored).
* tuning budget: 4 configurations per detector family, chosen by pooled PR-AUC on VAL.
  Neural: window in {16, 32} x bottleneck in {2, 4}, seed 0, early stopping on VAL reconstruction loss.
  Classical: Mahalanobis shrinkage in {0.0, 0.1, 0.3, 1.0}.
* seeds: the chosen neural configuration is retrained with 5 seeds; the classical detectors are
  deterministic (seed variance is exactly zero, which is itself a result).
* uncertainty: cluster bootstrap over test experiments (w3d5) for one fitted model of each kind.
Results are printed and written to lab/results/neural_vs_classical.json.
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

from flowguard.baselines import MahalanobisScorer, SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.metrics import pr_auc  # noqa: E402
from flowguard.splits import load_splits, validate_splits  # noqa: E402
from flowguard.uncertainty import cluster_bootstrap, paired_bootstrap_diff  # noqa: E402

BURN_IN = 100
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"


def pooled(tidy, scores) -> float:
    usable = tidy["t"].to_numpy() >= BURN_IN
    return pr_auc(tidy["anomaly"].to_numpy()[usable], np.asarray(scores)[usable])


def per_experiment(tidy, scores) -> dict:
    usable = tidy["t"].to_numpy() >= BURN_IN
    y, s, e = tidy["anomaly"].to_numpy(), np.asarray(scores), tidy["experiment_id"].to_numpy()
    return {exp: {"y": y[(e == exp) & usable], "s": s[(e == exp) & usable]} for exp in sorted(set(e))}


def pooled_from(results: list[dict]) -> float:
    return pr_auc(np.concatenate([r["y"] for r in results]), np.concatenate([r["s"] for r in results]))


def latency_ms_per_1000_rows(score_fn, frame, repeats: int = 3) -> float:
    best = float("inf")
    for _ in range(repeats):
        started = time.perf_counter()
        score_fn(frame)
        best = min(best, time.perf_counter() - started)
    return 1000.0 * best / len(frame) * 1000.0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Neural vs classical detectors on SKAB.")
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    ap.add_argument("--quick", action="store_true", help="1 neural config, 2 seeds (smoke run)")
    ap.add_argument("--out", default=str(HERE / "results" / "neural_vs_classical.json"))
    ap.add_argument("--threads", type=int, default=1,
                    help="torch intra-op threads (default 1: fastest for this tiny model; see the lesson)")
    args = ap.parse_args(argv)
    try:
        import torch

        from flowguard.neural import NeuralScorer
    except ImportError as exc:
        print(f"error: PyTorch is needed for this script ({exc}). See the lesson's set-up note.", file=sys.stderr)
        return 2
    torch.set_num_threads(args.threads)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(MANIFEST)          # frozen in w3d1; never redrawn
    validate_splits(manifest, tidy)
    folds = manifest["dev_folds"]
    fit = tidy[tidy["experiment_id"].isin(sum(folds[:3], []))].reset_index(drop=True)
    val = tidy[tidy["experiment_id"].isin(folds[3])].reset_index(drop=True)
    test = tidy[tidy["experiment_id"].isin(manifest["test"])].reset_index(drop=True)
    print(f"FIT {fit['experiment_id'].nunique()} experiments, VAL {val['experiment_id'].nunique()}, "
          f"TEST {test['experiment_id'].nunique()} (read once at the end)\n")
    out: dict = {"protocol": {"threads": args.threads, "burn_in": BURN_IN, "fit": sum(folds[:3], []), "val": folds[3],
                              "test": manifest["test"]}}

    # ---- 1. tuning on VAL, equal budget
    print("1. Tuning on VAL (pooled PR-AUC, rows t >= 100)")
    configs = [(32, 4)] if args.quick else [(16, 2), (16, 4), (32, 2), (32, 4)]
    neural_trials = []
    for window, bottleneck in configs:
        scorer = NeuralScorer(window=window, bottleneck=bottleneck, seed=0).fit(fit, val)
        trial = {"window": window, "bottleneck": bottleneck, "val_pr_auc": pooled(val, scorer.score(val)),
                 "best_epoch": scorer.history_["best_epoch"], "stopped_epoch": scorer.history_["stopped_epoch"],
                 "train_seconds": scorer.train_seconds_, "n_parameters": scorer.n_parameters_}
        neural_trials.append(trial)
        print(f"   neural window={window:>2} bottleneck={bottleneck}: VAL {trial['val_pr_auc']:.3f} "
              f"(best epoch {trial['best_epoch']}, stopped {trial['stopped_epoch']}, {trial['train_seconds']:.0f} s)")
    classical_trials = []
    for shrinkage in (0.0, 0.1, 0.3, 1.0):
        s = burn_in_scores(lambda k=shrinkage: MahalanobisScorer(k), val, BURN_IN)
        classical_trials.append({"shrinkage": shrinkage, "val_pr_auc": pooled(val, s)})
        print(f"   Mahalanobis shrinkage={shrinkage:.1f}: VAL {classical_trials[-1]['val_pr_auc']:.3f}")
    best_neural = max(neural_trials, key=lambda r: r["val_pr_auc"])
    best_classical = max(classical_trials, key=lambda r: r["val_pr_auc"])
    out["tuning"] = {"neural": neural_trials, "classical": classical_trials}
    print(f"   chosen: neural window={best_neural['window']} bottleneck={best_neural['bottleneck']}; "
          f"Mahalanobis shrinkage={best_classical['shrinkage']}\n")

    # ---- 2. seeds for the chosen neural configuration; TEST read here
    seeds = [0, 1] if args.quick else [0, 1, 2, 3, 4]
    print(f"2. Chosen neural configuration, {len(seeds)} seeds (FIT -> early stop on VAL -> TEST)")
    seed_rows, models = [], {}
    for seed in seeds:
        scorer = NeuralScorer(window=best_neural["window"], bottleneck=best_neural["bottleneck"], seed=seed)
        scorer.fit(fit, val)
        test_scores = scorer.score(test)
        models[seed] = (scorer, test_scores)
        seed_rows.append({"seed": seed, "val_pr_auc": pooled(val, scorer.score(val)),
                          "test_pr_auc": pooled(test, test_scores), "best_epoch": scorer.history_["best_epoch"],
                          "stopped_epoch": scorer.history_["stopped_epoch"], "train_seconds": scorer.train_seconds_,
                          "train_loss": scorer.history_["train_loss"], "val_loss": scorer.history_["val_loss"]})
        print(f"   seed {seed}: VAL {seed_rows[-1]['val_pr_auc']:.3f}  TEST {seed_rows[-1]['test_pr_auc']:.3f}  "
              f"best epoch {seed_rows[-1]['best_epoch']} (stopped {seed_rows[-1]['stopped_epoch']})  "
              f"{seed_rows[-1]['train_seconds']:.0f} s")
    test_values = np.array([r["test_pr_auc"] for r in seed_rows])
    print(f"   TEST over seeds: mean {test_values.mean():.3f}, sd {test_values.std(ddof=1):.3f}, "
          f"range [{test_values.min():.3f}, {test_values.max():.3f}]\n")
    out["neural_seeds"] = seed_rows

    # ---- 3. classical detectors on TEST
    classical = {
        f"Mahalanobis burn-in (shrinkage {best_classical['shrinkage']})":
            burn_in_scores(lambda: MahalanobisScorer(best_classical["shrinkage"]), test, BURN_IN),
        "flow_rate |z| burn-in (w2d6 best single sensor)":
            burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), test, BURN_IN),
    }
    # The seed shown with an interval is the median seed by VAL score: choosing it by TEST score would be
    # one more look at the test set.
    median_seed = sorted(seed_rows, key=lambda r: r["val_pr_auc"])[len(seed_rows) // 2]["seed"]
    neural_name = f"neural AE (seed {median_seed}, median seed by VAL)"
    detectors = {neural_name: models[median_seed][1], **classical}
    print("3. TEST, pooled PR-AUC with 95% cluster-bootstrap interval over the 7 test experiments")
    print("| detector | TEST PR-AUC [95% CI] |")
    print("|---|---|")
    results, out["test"] = {}, {}
    for name, s in detectors.items():
        results[name] = per_experiment(test, s)
        ci = cluster_bootstrap(pooled_from, results[name], n_boot=2000, seed=0)
        out["test"][name] = ci
        print(f"| {name} | {ci['estimate']:.3f} [{ci['low']:.3f}, {ci['high']:.3f}] |")
    for other in classical:
        d = paired_bootstrap_diff(pooled_from, results[neural_name], results[other], n_boot=2000, seed=0)
        out.setdefault("paired", {})[other] = d
        print(f"   neural minus {other}: {d['estimate']:+.3f} [{d['low']:+.3f}, {d['high']:+.3f}]")

    # ---- 4. cost
    scorer = models[median_seed][0]
    one_experiment = test[test["experiment_id"] == manifest["test"][0]]
    cost = {
        "neural": {"parameters": scorer.n_parameters_, "train_seconds_mean":
                   float(np.mean([r["train_seconds"] for r in seed_rows])),
                   "score_ms_per_1000_rows": latency_ms_per_1000_rows(scorer.score, one_experiment)},
        "mahalanobis": {"parameters": "8 means + 8 sds + 8x8 precision per experiment (burn-in)",
                        "train_seconds_mean": 0.0,
                        "score_ms_per_1000_rows": latency_ms_per_1000_rows(
                            lambda f: burn_in_scores(lambda: MahalanobisScorer(best_classical["shrinkage"]), f, BURN_IN),
                            one_experiment)},
    }
    out["cost"] = cost
    print("\n4. Cost (this machine)")
    print(f"   neural: {cost['neural']['parameters']} parameters, {cost['neural']['train_seconds_mean']:.0f} s "
          f"training per seed, {cost['neural']['score_ms_per_1000_rows']:.1f} ms per 1000 rows scored")
    print(f"   Mahalanobis: no training, {cost['mahalanobis']['score_ms_per_1000_rows']:.1f} ms per 1000 rows scored")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
