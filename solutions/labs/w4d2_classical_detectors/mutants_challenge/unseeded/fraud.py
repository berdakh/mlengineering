"""w4d2 challenge, reference solution: unsupervised vs supervised fraud scoring under label scarcity.

Decisions (defended in DECISION.md):
* features exclude identifiers and the label; card_age_days is kept (it is available at prediction
  time) but is a per-customer constant, which is exactly why validation must be grouped by customer;
* every estimate is out-of-fold with folds grouped by customer (GroupKFold), computed on the labelled
  rows only (the only rows whose truth is known);
* the isolation forest uses all training rows of the training-fold customers (labels not needed);
  the GBT uses only their labelled rows;
* the choice is the method with the higher grouped out-of-fold average precision; the returned
  model is refitted on all training rows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

FEATURES = ["amount", "hour", "distance_km", "merchant_risk", "online", "n_tx_24h", "card_age_days"]
N_FOLDS = 5


class Scorer:
    """Wraps a fitted estimator; score(df) uses FEATURES only, higher = more likely fraud."""

    def __init__(self, kind: str, model):
        self.kind, self.model = kind, model

    def score(self, df: pd.DataFrame) -> np.ndarray:
        x = df[FEATURES].to_numpy(dtype=float)
        if self.kind == "iforest":
            return -self.model.score_samples(x)
        return self.model.predict_proba(x)[:, 1]


def _fit(kind: str, df: pd.DataFrame, seed: int) -> Scorer:
    if kind == "iforest":
        model = IsolationForest(n_estimators=300, random_state=None).fit(df[FEATURES].to_numpy(dtype=float))
    else:
        lab = df[df["label"].notna()]
        model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                                               early_stopping=False, random_state=None)
        model.fit(lab[FEATURES].to_numpy(dtype=float), lab["label"].astype(int).to_numpy())
    return Scorer(kind, model)


def grouped_oof_ap(kind: str, train: pd.DataFrame, seed: int = 0) -> float:
    """Average precision on labelled rows, every row scored by a model that never saw its customer."""
    labelled = train["label"].notna().to_numpy()
    scores = np.full(len(train), np.nan)
    for fit_idx, held_idx in GroupKFold(n_splits=N_FOLDS).split(train, groups=train["customer_id"]):
        model = _fit(kind, train.iloc[fit_idx], seed)
        scores[held_idx] = model.score(train.iloc[held_idx])
    return float(average_precision_score(train.loc[labelled, "label"].astype(int), scores[labelled]))


def run(train: pd.DataFrame, seed: int = 0) -> dict:
    estimates = {kind: grouped_oof_ap(kind, train, seed) for kind in ("iforest", "gbt")}
    choice = max(estimates, key=estimates.get)
    return {"choice": choice, "estimates": estimates, "model": _fit(choice, train, seed)}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    here = Path(__file__).resolve()
    root = next(q for q in here.parents if (q / "project" / "get_skab.py").is_file())
    data = root / "labs" / "w4d2_classical_detectors" / "challenge" / "data"
    sys.path.insert(0, str(data))
    import make_transactions
    train, test = make_transactions.tables()
    out = run(train)
    print("estimates (grouped out-of-fold AP on labelled training rows):",
          {k: round(v, 3) for k, v in out["estimates"].items()}, "-> choice:", out["choice"])
    y = test["label"].astype(int).to_numpy()
    for kind in ("iforest", "gbt"):
        print(f"test AP, {kind}: {average_precision_score(y, _fit(kind, train, 0).score(test)):.3f}")
    print(f"test prevalence: {y.mean():.4f}")
