"""Three leakage mechanisms measured on PURE NOISE (SYNTHETIC), where the true AUC is 0.5 by construction.

    python lessons/w3d1_leakage/example/selection_leak_demo.py

1. Feature selection on all rows, then cross-validation   -> strongly optimistic
2. Standardisation on all rows, then cross-validation     -> wrong by construction, numerically tiny here
3. Best of N configurations judged on the test set        -> optimistic, grows with N

Because features and labels are independent, any AUC above 0.5 is manufactured by the procedure.
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

N_REPEATS = 20


def noise(rng, n: int, p: int):
    return rng.standard_normal((n, p)), rng.integers(0, 2, n)


def selection_experiment(n: int, p: int, k: int = 20, repeats: int = N_REPEATS, seed: int = 0) -> tuple[float, float]:
    """Mean CV AUC with selection outside the folds (leaky) and inside a Pipeline (correct)."""
    rng = np.random.default_rng(seed)
    leaky, correct = [], []
    for _ in range(repeats):
        X, y = noise(rng, n, p)
        cv = StratifiedKFold(5, shuffle=True, random_state=0)
        k_eff = min(k, p)
        X_sel = SelectKBest(f_classif, k=k_eff).fit_transform(X, y)              # sees every label
        leaky.append(cross_val_score(LogisticRegression(max_iter=1000), X_sel, y, cv=cv, scoring="roc_auc").mean())
        pipe = make_pipeline(SelectKBest(f_classif, k=k_eff), LogisticRegression(max_iter=1000))
        correct.append(cross_val_score(pipe, X, y, cv=cv, scoring="roc_auc").mean())
    return float(np.mean(leaky)), float(np.mean(correct))


def scaling_experiment(n: int = 100, p: int = 20, repeats: int = N_REPEATS, seed: int = 1) -> tuple[float, float]:
    """Mean CV AUC with the scaler fitted on all rows versus inside the folds."""
    rng = np.random.default_rng(seed)
    leaky, correct = [], []
    for _ in range(repeats):
        X, y = noise(rng, n, p)
        X = X * rng.lognormal(0, 1, p)                                          # give scaling something to do
        cv = StratifiedKFold(5, shuffle=True, random_state=0)
        leaky.append(cross_val_score(LogisticRegression(max_iter=1000), StandardScaler().fit_transform(X), y,
                                     cv=cv, scoring="roc_auc").mean())
        correct.append(cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), X, y,
                                       cv=cv, scoring="roc_auc").mean())
    return float(np.mean(leaky)), float(np.mean(correct))


def best_of_n_experiment(n: int = 200, p: int = 20, max_n: int = 50, repeats: int = N_REPEATS, seed: int = 2) -> dict[int, float]:
    """Mean of the best test AUC among the first N random configurations, for several N.

    A 'configuration' is a random subset of 5 features and a random C: none is better than another.
    """
    rng = np.random.default_rng(seed)
    checkpoints = [1, 2, 5, 10, 20, max_n]
    best = {c: [] for c in checkpoints}
    for _ in range(repeats):
        X, y = noise(rng, n, p)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)
        aucs = []
        for _ in range(max_n):
            cols = rng.choice(p, size=5, replace=False)
            model = LogisticRegression(C=10 ** rng.uniform(-2, 2), max_iter=1000).fit(X_tr[:, cols], y_tr)
            aucs.append(roc_auc_score(y_te, model.predict_proba(X_te[:, cols])[:, 1]))
        for c in checkpoints:
            best[c].append(max(aucs[:c]))
    return {c: float(np.mean(v)) for c, v in best.items()}


def main() -> None:
    print("1. feature selection (keep 20) outside vs inside the CV folds; true AUC = 0.5")
    print("   n     p   | selection on all rows | selection in pipeline")
    for n, p in [(100, 20), (100, 200), (100, 2000), (1000, 2000)]:
        leaky, correct = selection_experiment(n, p)
        print(f"   {n:<5d} {p:<5d}|        {leaky:.3f}          |        {correct:.3f}")
    leaky, correct = scaling_experiment()
    print(f"\n2. scaling on all rows vs in pipeline (n=100, p=20): {leaky:.3f} vs {correct:.3f}")
    print("\n3. best test AUC among N equally useless configurations (n=200, test 60 rows)")
    for n_configs, auc in best_of_n_experiment().items():
        print(f"   N = {n_configs:<3d} -> {auc:.3f}")


if __name__ == "__main__":
    main()
