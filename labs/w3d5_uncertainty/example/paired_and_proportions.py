"""Worked example 2: paired comparisons, small-count proportions, and seed variance.

SYNTHETIC data throughout.

    python labs/w3d5_uncertainty/example/paired_and_proportions.py     # about 6 s

Part 1  Two detectors scored on the same 12 experiments. B is a little worse than A on every
        experiment; experiments differ a lot in difficulty. Separate intervals overlap almost
        completely; the paired interval for the difference is narrow and excludes zero.
Part 2  How wide is an interval for "k of n events detected"? Wald vs Wilson vs exact.
Part 3  Seed variance is a different quantity from test-set variance: a random forest retrained
        with 20 seeds, evaluated on one fixed test set, next to the test-set bootstrap interval.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
from scipy.stats import binomtest, wilcoxon
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score


def percentile(values, level=0.95) -> tuple[float, float]:
    a = (1 - level) / 2
    return tuple(np.quantile(values, [a, 1 - a]))


def part1() -> None:
    rng = np.random.default_rng(7)
    n = 12
    difficulty = rng.normal(0.70, 0.15, size=n)                 # per-experiment score of detector B
    a = difficulty + 0.02 + rng.normal(0, 0.004, size=n)        # detector A: +0.02 everywhere
    b = difficulty
    draws = rng.integers(0, n, size=(4000, n))
    ci_a, ci_b = percentile(a[draws].mean(axis=1)), percentile(b[draws].mean(axis=1))
    paired = percentile((a - b)[draws].mean(axis=1))
    other = rng.integers(0, n, size=(4000, n))
    unpaired = percentile(a[draws].mean(axis=1) - b[other].mean(axis=1))
    d = a - b
    k = int(min((d > 0).sum(), (d < 0).sum()))
    sign_p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    print("Part 1: same 12 experiments, A = B + 0.02 on each")
    print(f"  mean A = {a.mean():.3f}  95% CI [{ci_a[0]:.3f}, {ci_a[1]:.3f}]")
    print(f"  mean B = {b.mean():.3f}  95% CI [{ci_b[0]:.3f}, {ci_b[1]:.3f}]   <- the two intervals overlap")
    print(f"  difference A - B = {d.mean():+.4f}")
    print(f"    unpaired bootstrap of the difference: [{unpaired[0]:+.3f}, {unpaired[1]:+.3f}]  (includes 0)")
    print(f"    paired bootstrap of the difference:   [{paired[0]:+.4f}, {paired[1]:+.4f}]  (excludes 0)")
    print(f"    A better on {int((d > 0).sum())}/{n} experiments; sign test p = {sign_p:.4f}; "
          f"Wilcoxon signed-rank p = {wilcoxon(d).pvalue:.4f}")
    print(f"  sd of per-experiment scores {b.std(ddof=1):.3f}; sd of per-experiment differences {d.std(ddof=1):.4f}")
    r = np.corrcoef(a, b)[0, 1]
    print(f"  correlation between A and B across experiments: {r:.4f}\n")


def part2() -> None:
    z = NormalDist().inv_cdf(0.975)
    print("Part 2: 95% intervals for a detection rate k/n")
    print("  | k/n | Wald (normal approx.) | Wilson | exact (Clopper-Pearson) |")
    print("  |---|---|---|---|")
    for k, n in [(7, 9), (9, 9), (1, 9), (27, 34), (34, 34), (70, 90), (700, 900)]:
        p = k / n
        half = z * math.sqrt(p * (1 - p) / n)
        w = binomtest(k, n).proportion_ci(method="wilson")
        e = binomtest(k, n).proportion_ci(method="exact")
        print(f"  | {k}/{n} | [{p - half:.3f}, {p + half:.3f}] | [{w.low:.3f}, {w.high:.3f}] | [{e.low:.3f}, {e.high:.3f}] |")
    print()


def part3() -> None:
    rng = np.random.default_rng(3)

    def make(n_clusters: int):
        xs, ys, gs = [], [], []
        for g in range(n_clusters):
            shift = rng.normal(0, 1.0, size=6)                  # cluster-specific offset of the features
            x = rng.normal(0, 1, size=(60, 6)) + shift
            logit = 1.2 * (x[:, 0] - shift[0]) - 0.8 * (x[:, 1] - shift[1]) + rng.normal(0, 0.5)
            ys.append((rng.random(60) < 1 / (1 + np.exp(-logit))).astype(int))
            xs.append(x)
            gs.append(np.full(60, g))
        return np.vstack(xs), np.concatenate(ys), np.concatenate(gs)

    x_train, y_train, _ = make(25)
    x_test, y_test, g_test = make(9)
    aucs, scores = [], None
    for seed in range(20):
        model = RandomForestClassifier(n_estimators=30, random_state=seed).fit(x_train, y_train)
        s = model.predict_proba(x_test)[:, 1]
        aucs.append(roc_auc_score(y_test, s))
        scores = s if seed == 0 else scores
    reps = []
    for _ in range(2000):
        drawn = rng.integers(0, 9, size=9)
        idx = np.concatenate([np.flatnonzero(g_test == g) for g in drawn])
        reps.append(roc_auc_score(y_test[idx], scores[idx]))
    low, high = percentile(reps)
    print("Part 3: one fixed test set of 9 clusters, random forest retrained with 20 seeds")
    print(f"  ROC AUC over seeds: mean {np.mean(aucs):.3f}, sd {np.std(aucs, ddof=1):.4f}, "
          f"range [{min(aucs):.3f}, {max(aucs):.3f}]      <- optimisation/seed noise")
    print(f"  seed-0 model, cluster bootstrap over the 9 test clusters: {aucs[0]:.3f} [{low:.3f}, {high:.3f}]"
          "   <- test-set sampling")
    print(f"  interval half-width {(high - low) / 2:.3f} is {(high - low) / 2 / np.std(aucs, ddof=1):.0f}x the seed sd here; "
          "report both, never one as the other")


if __name__ == "__main__":
    part1()
    part2()
    part3()
