""""Marketing touches predict conversion with AUC 0.9" - the analysis behind the slide.

    python lessons/w3d1_leakage/challenge/published_analysis.py

It is tidy, it cross-validates, it uses a held-out test set. Two of its steps make the
reported number meaningless. Find them, measure them, and replace the number.
Data: leads.csv (SYNTHETIC, 240 leads x 300 features).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent


def published_estimate(X: pd.DataFrame, y: pd.Series) -> dict:
    # Step 1: keep the 20 touches most associated with conversion
    selector = SelectKBest(f_classif, k=20).fit(X, y)
    X_sel = StandardScaler().fit_transform(selector.transform(X))

    # Step 2: 5-fold cross-validation of the model on the selected touches
    cv_auc = cross_val_score(LogisticRegression(C=1.0, max_iter=2000), X_sel, y, cv=5, scoring="roc_auc").mean()

    # Step 3: a held-out test set, to be safe - try a few configurations and keep the best
    best = {"auc": -np.inf}
    for seed in range(10):
        X_tr, X_te, y_tr, y_te = train_test_split(X_sel, y, test_size=0.25, random_state=seed, stratify=y)
        for C in (0.01, 0.1, 1.0, 10.0):
            model = LogisticRegression(C=C, max_iter=2000).fit(X_tr, y_tr)
            auc = roc_auc_score(y_te, model.predict_proba(X_te)[:, 1])
            if auc > best["auc"]:
                best = {"auc": auc, "seed": seed, "C": C}
    return {"cv_auc": float(cv_auc), "test_auc": float(best["auc"]), "chosen": best}


if __name__ == "__main__":
    data = pd.read_csv(HERE / "leads.csv")
    result = published_estimate(data.drop(columns="converted"), data["converted"])
    print(f"cross-validated AUC: {result['cv_auc']:.3f}")
    print(f"held-out test AUC:   {result['test_auc']:.3f}   (split seed {result['chosen']['seed']}, C={result['chosen']['C']})")
