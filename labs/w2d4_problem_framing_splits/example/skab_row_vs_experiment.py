"""Worked example, part 4 (REAL data): row-level vs experiment-level validation on SKAB.

Uses only the DEVELOPMENT experiments of the frozen manifest; the test set is not opened.
Needs the download first:  python project/get_skab.py

    python labs/w2d4_problem_framing_splits/example/skab_row_vs_experiment.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "solutions" / "labs" / "w2d4_problem_framing_splits" / "lab"
sys.path.insert(0, str(REFERENCE / "src"))          # the flowguard.data snapshot (same file as in lab/)
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402

RAW = ROOT / "data" / "raw" / "skab"


def scores(X_tr, y_tr, X_te, y_te) -> tuple[float, float]:
    model = RandomForestClassifier(n_estimators=100, min_samples_leaf=5, random_state=0, n_jobs=1)
    p = model.fit(X_tr, y_tr).predict_proba(X_te)[:, 1]
    return average_precision_score(y_te, p), roc_auc_score(y_te, p)


def main() -> int:
    try:
        tidy = load_raw(RAW)
    except FileNotFoundError as exc:
        print(exc)
        return 1
    manifest = json.loads((REFERENCE / "splits" / "v1.json").read_text())
    folds = manifest["dev_folds"]
    dev = tidy[tidy["experiment_id"].isin([e for f in folds for e in f])].reset_index(drop=True)
    X, y = dev[list(SENSOR_COLUMNS)].to_numpy(), dev["anomaly"].to_numpy()
    print(f"development pool: {dev['experiment_id'].nunique()} experiments, {len(dev)} rows, "
          f"positive fraction {y.mean():.3f}")

    row = [scores(X[tr], y[tr], X[te], y[te]) for tr, te in KFold(4, shuffle=True, random_state=0).split(X)]
    exp = []
    for held in folds:
        te = dev["experiment_id"].isin(held).to_numpy()
        exp.append(scores(X[~te], y[~te], X[te], y[te]))
    for name, res in (("row-level 4-fold       ", row), ("experiment-level 4-fold", exp)):
        ap, auc = np.array(res).T
        print(f"{name}  PR-AUC {ap.mean():.3f} (folds {ap.min():.3f}-{ap.max():.3f})   "
              f"ROC-AUC {auc.mean():.3f} (folds {auc.min():.3f}-{auc.max():.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
