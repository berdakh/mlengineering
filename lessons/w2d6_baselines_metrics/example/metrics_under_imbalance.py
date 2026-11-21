"""Worked example (SYNTHETIC data): how metrics behave when prevalence changes, and what calibration buys.

    python lessons/w2d6_baselines_metrics/example/metrics_under_imbalance.py

Part 1 holds the classifier fixed and changes only the class balance.
Part 2 fits two logistic regressions on a 4%-positive problem and compares ranking with calibration.
Part 3 turns costs into a threshold and shows what miscalibration does to the decision.

Synthetic Gaussian data: it demonstrates properties of the METRICS, which hold for any data.
It says nothing about any real detector.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve, roc_auc_score
from sklearn.model_selection import train_test_split


def part1_prevalence() -> None:
    print("Part 1 - same score distributions, different prevalence (n = 400,000 rows each)")
    print(f"{'prevalence':>10} {'ROC AUC':>8} {'PR-AUC':>7} {'floor':>6} {'P@R=0.8':>8} {'acc(all-neg)':>13}")
    rng = np.random.default_rng(0)
    for prevalence in (0.35, 0.05, 0.005):
        n = 400_000
        y = (rng.random(n) < prevalence).astype(int)
        score = rng.standard_normal(n) + 1.5 * y            # negatives N(0,1), positives N(1.5,1)
        precision, recall, _ = precision_recall_curve(y, score)
        p_at_r80 = precision[recall >= 0.8].max()
        print(f"{prevalence:>10.3f} {roc_auc_score(y, score):>8.3f} {average_precision_score(y, score):>7.3f} "
              f"{y.mean():>6.3f} {p_at_r80:>8.3f} {1 - y.mean():>13.3f}")


def reliability_table(y: np.ndarray, p: np.ndarray, edges: np.ndarray) -> list[tuple[str, int, float, float]]:
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        inside = (p >= lo) & (p < hi) if hi < 1.0 else (p >= lo) & (p <= hi)
        if inside.any():
            rows.append((f"[{lo:.2f}, {hi:.2f})", int(inside.sum()), float(p[inside].mean()), float(y[inside].mean())))
    return rows


def part2_and_3() -> None:
    rng = np.random.default_rng(1)
    n = 60_000
    X = rng.standard_normal((n, 4))
    logit = -4.2 + 1.2 * X[:, 0] + 0.8 * X[:, 1] - 0.6 * X[:, 2]
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    X_fit, X_eval, y_fit, y_eval = train_test_split(X, y, test_size=0.5, random_state=0, stratify=y)
    models = {
        "plain": LogisticRegression(max_iter=1000).fit(X_fit, y_fit),
        "class_weight='balanced'": LogisticRegression(max_iter=1000, class_weight="balanced").fit(X_fit, y_fit),
    }
    print(f"\nPart 2 - two logistic regressions, prevalence {y_eval.mean():.3f}")
    print(f"{'model':<26}{'ROC AUC':>8}{'PR-AUC':>8}{'Brier':>8}{'mean p':>8}")
    probabilities = {}
    for name, model in models.items():
        p = model.predict_proba(X_eval)[:, 1]
        probabilities[name] = p
        print(f"{name:<26}{roc_auc_score(y_eval, p):>8.3f}{average_precision_score(y_eval, p):>8.3f}"
              f"{brier_score_loss(y_eval, p):>8.4f}{p.mean():>8.3f}")
    print(f"{'constant = prevalence':<26}{'0.500':>8}{y_eval.mean():>8.3f}"
          f"{brier_score_loss(y_eval, np.full(len(y_eval), y_fit.mean())):>8.4f}{y_fit.mean():>8.3f}")
    edges = np.array([0.0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0])
    for name, p in probabilities.items():
        print(f"\nreliability of {name}:  bin, rows, mean predicted, observed rate")
        for label, count, predicted, observed in reliability_table(y_eval, p, edges):
            print(f"  {label:<14}{count:>7}{predicted:>9.3f}{observed:>9.3f}")

    # Part 3: act when expected benefit exceeds expected cost.
    cost_action, benefit_if_positive = 5.0, 60.0
    threshold = cost_action / benefit_if_positive          # act iff p >= C / B
    print(f"\nPart 3 - act iff p >= cost/benefit = {cost_action:.0f}/{benefit_if_positive:.0f} = {threshold:.3f}")
    print(f"{'model':<26}{'acted on':>9}{'precision':>10}{'net value per 1,000 rows':>26}")
    for name, p in probabilities.items():
        act = p >= threshold
        net = (benefit_if_positive * y_eval[act].sum() - cost_action * act.sum()) / len(y_eval) * 1000
        print(f"{name:<26}{act.mean():>9.3f}{y_eval[act].mean():>10.3f}{net:>26.1f}")
    for name, act in (("act on nobody", np.zeros(len(y_eval), bool)), ("act on everybody", np.ones(len(y_eval), bool))):
        net = (benefit_if_positive * y_eval[act].sum() - cost_action * act.sum()) / len(y_eval) * 1000
        print(f"{name:<26}{act.mean():>9.3f}{'-':>10}{net:>26.1f}")


if __name__ == "__main__":
    part1_prevalence()
    part2_and_3()
