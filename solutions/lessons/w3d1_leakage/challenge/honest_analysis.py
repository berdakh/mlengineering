"""Reference: an estimate in which every data-dependent step is inside the resampling loop.

    python solutions/lessons/w3d1_leakage/challenge/honest_analysis.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

GRID = {"clf__C": [0.01, 0.1, 1.0, 10.0]}


def build_search(seed: int) -> GridSearchCV:
    """Selection + scaling + model as ONE estimator; C is tuned by an inner cross-validation."""
    pipe = Pipeline([
        ("select", SelectKBest(f_classif, k=20)),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000)),
    ])
    inner = StratifiedKFold(n_splits=4, shuffle=True, random_state=seed)
    return GridSearchCV(pipe, GRID, scoring="roc_auc", cv=inner)


def honest_estimate(X: pd.DataFrame, y: pd.Series, seed: int = 0) -> dict:
    """Nested cross-validation: the outer folds never influence selection, scaling or the choice of C.

    The estimate is the AUC of the pooled out-of-fold predictions. The returned model is the same
    procedure refitted on all rows; the estimate describes that procedure, not one particular fit.
    """
    y = pd.Series(y).reset_index(drop=True)
    X = X.reset_index(drop=True)
    outer = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    oof = np.zeros(len(y))
    for train, test in outer.split(X, y):
        search = build_search(seed).fit(X.iloc[train], y.iloc[train])
        oof[test] = search.predict_proba(X.iloc[test])[:, 1]
    model = build_search(seed).fit(X, y)
    return {"auc": float(roc_auc_score(y, oof)), "model": model}


if __name__ == "__main__":
    here = Path(__file__).resolve()
    data = here.parent / "leads.csv"
    if not data.is_file():
        data = here.parents[4] / "lessons" / "w3d1_leakage" / "challenge" / "leads.csv"
    frame = pd.read_csv(data)
    result = honest_estimate(frame.drop(columns="converted"), frame["converted"])
    print(f"honest AUC estimate: {result['auc']:.3f}")
