"""Six validation schemes, two models, one dataset: what each scheme reports on the REAL SKAB data.

    python project/get_skab.py                                              # once, from the repo root
    python lessons/w3d2_group_temporal_validation/lab/compare_schemes.py    # prints the table

Only the DEVELOPMENT experiments of the v2 manifest are used; the test set is not opened.
Rows with t < BURN_IN are used for per-experiment calibration and are never trained on or scored.

This file is complete. It works once you have implemented flowguard.validation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.splits import dev_experiments, find_overlap_groups, make_splits, validate_splits  # noqa: E402
from flowguard.validation import (forward_chaining_split, grouped_folds, leave_one_family_out,  # noqa: E402
                                  purged_time_split, required_purge, rows_for)

BURN_IN = 100        # rows at the start of each experiment used for calibration (all normal)
WINDOW = 30          # causal rolling-mean window, in rows (about 30 s)
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"


def burn_in_features(dev: pd.DataFrame) -> np.ndarray:
    """Per experiment: z-score each sensor against its own first BURN_IN rows (clipped to +-20), plus
    the causal rolling mean of that z over the last WINDOW rows. No feature uses t or datetime."""
    parts = []
    for _, g in dev.groupby("experiment_id", sort=False):
        x = g[list(SENSOR_COLUMNS)].to_numpy(dtype=float)
        mean, std = x[:BURN_IN].mean(axis=0), x[:BURN_IN].std(axis=0)
        z = np.clip((x - mean) / np.where(std > 0, std, 1.0), -20.0, 20.0)
        rolled = pd.DataFrame(z).rolling(WINDOW, min_periods=1).mean().to_numpy()
        parts.append(pd.DataFrame(np.hstack([z, rolled]), index=g.index))
    return pd.concat(parts).loc[dev.index].to_numpy()


MODELS = {
    "random forest on raw sensor values": (
        lambda dev: dev[list(SENSOR_COLUMNS)].to_numpy(dtype=float),
        lambda: RandomForestClassifier(n_estimators=100, min_samples_leaf=5, random_state=0, n_jobs=1)),
    "logistic regression on burn-in z + rolling mean": (
        burn_in_features,
        lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))),
}


def schemes(dev: pd.DataFrame, manifest: dict, groups: list[set[str]]) -> dict[str, list[tuple[str, np.ndarray, np.ndarray]]]:
    """name -> list of (fold label, train row positions, validation row positions) over ``dev``."""
    usable = dev["t"].to_numpy() >= BURN_IN
    position = np.arange(len(dev))
    out: dict[str, list] = {}

    rows = position[usable]
    out["1 rows, shuffled 4-fold"] = [
        (str(k), rows[tr], rows[va]) for k, (tr, va) in enumerate(KFold(4, shuffle=True, random_state=0).split(rows))]

    for name, buffer in (("2 time blocks within experiment, no buffer", 0),
                         (f"3 time blocks within experiment, purge = embargo = {required_purge(WINDOW)}",
                          required_purge(WINDOW))):
        folds = [([], []) for _ in range(4)]
        for _, g in dev[usable].groupby("experiment_id", sort=False):
            pos = position[g.index.to_numpy()]                    # dev has a RangeIndex
            for k, (tr, va) in enumerate(purged_time_split(len(pos), 4, purge=buffer, embargo=buffer)):
                folds[k][0].append(pos[tr])
                folds[k][1].append(pos[va])
        out[name] = [(f"block {k}", np.concatenate(tr), np.concatenate(va)) for k, (tr, va) in enumerate(folds)]

    out["4 experiments held out (manifest folds)"] = [
        (f"fold {k}", position[rows_for(dev, tr) & usable], position[rows_for(dev, va) & usable])
        for k, (tr, va) in enumerate(grouped_folds(manifest))]

    out["5 one family held out"] = [
        (family, position[rows_for(dev, tr) & usable], position[rows_for(dev, va) & usable])
        for family, tr, va in leave_one_family_out(dev, keep_together=groups)]

    day = dev.groupby("experiment_id")["datetime"].transform("min").dt.date.to_numpy()
    days = sorted(set(day))
    out["6 forward by recording day"] = [
        (f"train {len(tr)} day(s) -> {days[va[0]]}",
         position[np.isin(day, [days[i] for i in tr]) & usable],
         position[np.isin(day, [days[i] for i in va]) & usable])
        for tr, va in forward_chaining_split(len(days), len(days) - 1)]
    return out


def evaluate(X: np.ndarray, y: np.ndarray, make_model, folds) -> tuple[float, float, list[tuple[str, float]]]:
    """Pooled out-of-fold PR-AUC and ROC-AUC, and the per-fold ROC-AUC where both classes occur."""
    truth, score, per_fold = [], [], []
    for label, train, val in folds:
        p = make_model().fit(X[train], y[train]).predict_proba(X[val])[:, 1]
        truth.append(y[val])
        score.append(p)
        if 0 < y[val].sum() < len(val):
            per_fold.append((label, roc_auc_score(y[val], p)))
    truth, score = np.concatenate(truth), np.concatenate(score)
    return average_precision_score(truth, score), roc_auc_score(truth, score), per_fold


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compare validation schemes on SKAB (development experiments).")
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    groups = find_overlap_groups(tidy)
    manifest = make_splits(tidy, seed=0, keep_together=groups)
    validate_splits(manifest, tidy)
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))].reset_index(drop=True)
    y = dev["anomaly"].to_numpy()
    usable = dev["t"].to_numpy() >= BURN_IN
    print(f"development pool: {dev['experiment_id'].nunique()} experiments, {int(usable.sum())} usable rows, "
          f"positive fraction {y[usable].mean():.3f}; test experiments not opened\n")
    all_schemes = schemes(dev, manifest, groups)
    for model_name, (make_features, make_model) in MODELS.items():
        X = make_features(dev)
        print(f"### {model_name}\n")
        print("| scheme | folds | pooled PR-AUC | pooled ROC-AUC | ROC-AUC per fold |")
        print("|---|---|---|---|---|")
        for name, folds in all_schemes.items():
            ap_, auc, per_fold = evaluate(X, y, make_model, folds)
            detail = ", ".join(f"{label}: {value:.3f}" for label, value in per_fold)
            print(f"| {name} | {len(folds)} | {ap_:.3f} | {auc:.3f} | {detail} |")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
