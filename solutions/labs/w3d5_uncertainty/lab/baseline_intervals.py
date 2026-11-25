"""Intervals and paired comparisons for the w2d6 baselines on the REAL SKAB data.

    python project/get_skab.py                                   # once, from the repo root
    python labs/w3d5_uncertainty/lab/baseline_intervals.py    # about 1 minute

This file is complete. It works once you have implemented flowguard.uncertainty.

Unit of resampling: the OVERLAP GROUP. SKAB files that share identical rows (other/2-3-4,
other/10-11, other/12-13) are one cluster each, because they are not independent recordings.
Every other experiment is its own cluster. What the intervals cover: which clusters happened to be
evaluated, with models and thresholds held fixed. Not covered: refitting, other operating regimes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "splits" / "v2.json"  # frozen split manifest from w3d1
sys.path.insert(0, str(HERE / "src"))

from flowguard.baselines import MahalanobisScorer, SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.metrics import best_f1_threshold, pr_auc  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402
from flowguard.uncertainty import (cluster_bootstrap, paired_bootstrap_diff,  # noqa: E402
                                   paired_permutation_test, sign_test, wilson_interval)

BURN_IN = 100
N_BOOT = 2000
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"


# ----------------------------------------------------------------------------- scores (as in w2d6)
def burn_in_abs_z(tidy, n_burn: int) -> np.ndarray:
    cols = [burn_in_scores(lambda s=sensor: SingleSensorZScorer(s), tidy, n_burn) for sensor in SENSOR_COLUMNS]
    return np.clip(np.column_stack(cols), 0.0, 20.0)


def supervised_scores(tidy, manifest: dict, n_burn: int) -> np.ndarray:
    """Logistic regression on burn-in |z|; dev rows out-of-fold, test rows from a model fitted on all dev."""
    features = burn_in_abs_z(tidy, n_burn)
    y = tidy["anomaly"].to_numpy()
    usable = tidy["t"].to_numpy() >= n_burn
    experiment = tidy["experiment_id"]
    scores = np.zeros(len(tidy))
    for fold in manifest["dev_folds"]:
        held_out = experiment.isin(fold).to_numpy()
        train = experiment.isin([e for e in dev_experiments(manifest) if e not in fold]).to_numpy() & usable
        scores[held_out] = LogisticRegression(max_iter=2000).fit(features[train], y[train]).predict_proba(features[held_out])[:, 1]
    all_dev = experiment.isin(dev_experiments(manifest)).to_numpy() & usable
    is_test = experiment.isin(manifest["test"]).to_numpy()
    scores[is_test] = LogisticRegression(max_iter=2000).fit(features[all_dev], y[all_dev]).predict_proba(features[is_test])[:, 1]
    return scores


# ----------------------------------------------------------------------------- clusters and metrics
def cluster_ids(manifest: dict, experiments: list[str]) -> dict[str, str]:
    """experiment_id -> cluster id (the overlap group joined with '+', or the experiment itself)."""
    group_of = {e: "+".join(g) for g in manifest["overlap_groups"] for e in g}
    return {e: group_of.get(e, e) for e in experiments}


def per_cluster(tidy, scores: np.ndarray, experiments: list[str], cluster_of: dict[str, str]) -> dict[str, dict]:
    """{cluster_id: {"y": ..., "s": ..., "parts": [(y, s) per experiment]}} for rows with t >= BURN_IN."""
    out: dict[str, dict] = {}
    usable = tidy["t"].to_numpy() >= BURN_IN
    y_all = tidy["anomaly"].to_numpy()
    exp = tidy["experiment_id"].to_numpy()
    for e in experiments:
        rows = (exp == e) & usable
        entry = out.setdefault(cluster_of[e], {"parts": []})
        entry["parts"].append((y_all[rows], scores[rows]))
    for entry in out.values():
        entry["y"] = np.concatenate([p[0] for p in entry["parts"]])
        entry["s"] = np.concatenate([p[1] for p in entry["parts"]])
    return out


def pooled_pr_auc(results: list[dict]) -> float:
    """PR-AUC over all rows of the drawn clusters (rows of long experiments weigh more)."""
    return pr_auc(np.concatenate([r["y"] for r in results]), np.concatenate([r["s"] for r in results]))


def cluster_ap(result: dict) -> float:
    return pr_auc(result["y"], result["s"])


def row_bootstrap(y: np.ndarray, s: np.ndarray, n_boot: int, seed: int) -> tuple[float, float]:
    """The WRONG interval, for contrast only: rows resampled as if they were independent."""
    rng = np.random.default_rng(seed)
    reps = [pr_auc(y[i], s[i]) for i in (rng.integers(0, len(y), size=len(y)) for _ in range(n_boot))]
    low, high = np.nanquantile(reps, [0.025, 0.975])
    return float(low), float(high)


def fmt(ci: dict) -> str:
    return f"{ci['estimate']:.3f} [{ci['low']:.3f}, {ci['high']:.3f}]"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Intervals for the SKAB baselines.")
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(MANIFEST)  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    validate_splits(manifest, tidy)
    test, dev = manifest["test"], dev_experiments(manifest)
    labelled = sorted(test + dev)
    cluster_of = cluster_ids(manifest, labelled)

    scores = {
        "elapsed time t (no sensors)": tidy["t"].to_numpy(dtype=float),
        "flow_rate abs z, burn-in": burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN),
        "Mahalanobis, burn-in": burn_in_scores(MahalanobisScorer, tidy, BURN_IN),
        "logistic regression (supervised)": supervised_scores(tidy, manifest, BURN_IN),
    }
    label_free = [n for n in scores if "logistic" not in n]
    n_test_clusters = len({cluster_of[e] for e in test})
    n_all_clusters = len({cluster_of[e] for e in labelled})
    print(f"split v2: {len(test)} test experiments = {n_test_clusters} independent clusters; "
          f"{len(labelled)} labelled experiments = {n_all_clusters} clusters; n_boot = {args.n_boot}\n")

    # ---- A. test set
    print("A. Test set, pooled point-level PR-AUC, 95% intervals")
    print("| baseline | cluster bootstrap (correct unit) | row bootstrap (wrong unit) | width ratio |")
    print("|---|---|---|---|")
    test_results = {}
    for name, s in scores.items():
        res = per_cluster(tidy, s, test, cluster_of)
        test_results[name] = res
        ci = cluster_bootstrap(pooled_pr_auc, res, n_boot=args.n_boot, seed=0)
        y = np.concatenate([r["y"] for r in res.values()])
        sc = np.concatenate([r["s"] for r in res.values()])
        low, high = row_bootstrap(y, sc, n_boot=300, seed=0)
        ratio = (ci["high"] - ci["low"]) / (high - low)
        print(f"| {name} | {fmt(ci)} | [{low:.3f}, {high:.3f}] | {ratio:.1f}x |")

    # ---- B. all labelled experiments, label-free scorers only
    print("\nB. All labelled experiments (valid only for scorers that were never fitted to labels)")
    print("| baseline | pooled PR-AUC | mean per-cluster PR-AUC |")
    print("|---|---|---|")
    all_results = {}
    for name in label_free:
        res = per_cluster(tidy, scores[name], labelled, cluster_of)
        all_results[name] = res
        pooled = cluster_bootstrap(pooled_pr_auc, res, n_boot=args.n_boot, seed=0)
        macro = cluster_bootstrap(lambda rs: float(np.mean([cluster_ap(r) for r in rs])), res,
                                  n_boot=args.n_boot, seed=0)
        print(f"| {name} | {fmt(pooled)} | {fmt(macro)} |")

    # ---- C. paired comparisons
    print("\nC. Paired comparisons (difference in pooled PR-AUC, A minus B)")
    print("| A | B | data | clusters | difference [95% CI] | A better in | sign test p | permutation p |")
    print("|---|---|---|---|---|---|---|---|")
    comparisons = [
        ("logistic regression (supervised)", "flow_rate abs z, burn-in", "test", test_results),
        ("Mahalanobis, burn-in", "flow_rate abs z, burn-in", "test", test_results),
        ("Mahalanobis, burn-in", "flow_rate abs z, burn-in", "all labelled", all_results),
        ("flow_rate abs z, burn-in", "elapsed time t (no sensors)", "all labelled", all_results),
    ]
    for a, b, where, pool in comparisons:
        ra, rb = pool[a], pool[b]
        ci = paired_bootstrap_diff(pooled_pr_auc, ra, rb, n_boot=args.n_boot, seed=0)
        diffs = np.array([cluster_ap(ra[c]) - cluster_ap(rb[c]) for c in ra])
        print(f"| {a} | {b} | {where} | {len(diffs)} | {ci['estimate']:+.3f} [{ci['low']:+.3f}, {ci['high']:+.3f}] | "
              f"{int((diffs > 0).sum())}/{len(diffs)} | {sign_test(diffs):.4f} | "
              f"{paired_permutation_test(diffs, seed=0):.4f} |")

    # ---- D. a proportion with very few trials
    print("\nD. Event-level sanity count on the test set (threshold = best F1 on dev; an event counts as")
    print("   detected if at least one of its rows is flagged; false alarms are NOT counted, see w3d4)")
    print("| baseline | events detected | Wilson 95% interval |")
    print("|---|---|---|")
    for name in ("flow_rate abs z, burn-in", "logistic regression (supervised)"):
        s = scores[name]
        dev_res = per_cluster(tidy, s, dev, cluster_of)
        threshold, _ = best_f1_threshold(np.concatenate([r["y"] for r in dev_res.values()]),
                                         np.concatenate([r["s"] for r in dev_res.values()]))
        hits = sum(bool(np.any(sc[y == 1] >= threshold))
                   for r in test_results[name].values() for y, sc in r["parts"])
        low, high = wilson_interval(hits, len(test))
        print(f"| {name} | {hits}/{len(test)} | [{low:.2f}, {high:.2f}] |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
