"""Worked example, part 1 (SYNTHETIC): what within-group dependence does to K-fold.

    python labs/w3d2_group_temporal_validation/example/group_dependence.py

Data-generating process, per machine g and row i:
    x_signal  ~ N(0, 1)                       one feature that truly predicts the label everywhere
    u_g       ~ N(0, sigma_u^2)               a machine-level offset of the LABEL (not of x_signal)
    fingerprint_g in R^4                      features that identify the machine and nothing else
    y = 1[ x_signal + u_g + noise > 0 ]
The intraclass correlation of the latent label is  rho = sigma_u^2 / (sigma_u^2 + 1 + sigma_noise^2).
A flexible model can learn "machine g tends to be positive" from the fingerprint. That knowledge is
worthless on a new machine. Truth = accuracy on 300 machines never seen in any form.

Nothing here says anything about real equipment; it isolates one mechanism.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, KFold

N_MACHINES, ROWS_PER_MACHINE, NOISE = 20, 100, 0.5


def simulate(n_machines: int, rho: float, rng: np.random.Generator):
    sigma_u = np.sqrt(rho * (1 + NOISE ** 2) / (1 - rho)) if rho > 0 else 0.0
    groups = np.repeat(np.arange(n_machines), ROWS_PER_MACHINE)
    u = rng.normal(0, sigma_u, n_machines)[groups]
    fingerprint = rng.normal(0, 1, (n_machines, 4))[groups] + 0.05 * rng.standard_normal((len(groups), 4))
    x_signal = rng.standard_normal(len(groups))
    y = (x_signal + u + NOISE * rng.standard_normal(len(groups)) > 0).astype(int)
    return np.column_stack([x_signal, fingerprint]), y, groups


def model():
    return RandomForestClassifier(n_estimators=100, min_samples_leaf=3, random_state=0, n_jobs=1)


def cv_accuracy(X, y, folds) -> float:
    return float(np.mean([np.mean(model().fit(X[tr], y[tr]).predict(X[va]) == y[va]) for tr, va in folds]))


RHOS = (0.0, 0.2, 0.5, 0.8)


def part_a() -> list[dict]:
    """Mean over 5 repetitions of row-wise K-fold, machine-wise K-fold and the truth, per ICC."""
    out = []
    for rho in RHOS:
        rows, grouped, truth = [], [], []
        for rep in range(5):
            rng = np.random.default_rng(1000 * rep + int(100 * rho))
            X, y, g = simulate(N_MACHINES, rho, rng)
            rows.append(cv_accuracy(X, y, KFold(5, shuffle=True, random_state=0).split(X)))
            grouped.append(cv_accuracy(X, y, GroupKFold(5).split(X, y, g)))
            X_new, y_new, _ = simulate(300, rho, rng)
            truth.append(float(np.mean(model().fit(X, y).predict(X_new) == y_new)))
        out.append({"rho": rho, "row": float(np.mean(rows)), "group": float(np.mean(grouped)),
                    "truth": float(np.mean(truth))})
    return out


def main() -> None:
    print("Part A - optimism of row-wise K-fold as within-machine correlation grows (mean of 5 repetitions)")
    print("| ICC rho | row 5-fold | machine 5-fold | truth: new machines | row optimism |")
    print("|---|---|---|---|---|")
    for r in part_a():
        print(f"| {r['rho']:.1f} | {r['row']:.3f} | {r['group']:.3f} | {r['truth']:.3f} | "
              f"{r['row'] - r['truth']:+.3f} |")

    print("\nPart B - effective sample size: spread of a per-row accuracy over 2,000 simulated test sets")
    print("of 20 machines x 100 rows, when correctness is correlated within a machine (rho_e)")
    print("| rho_e | naive SE sqrt(p(1-p)/n) | simulated SE | ratio^2 (design effect) | 1 + (m-1) rho_e |")
    print("|---|---|---|---|---|")
    rng = np.random.default_rng(7)
    n, m, p = N_MACHINES * ROWS_PER_MACHINE, ROWS_PER_MACHINE, 0.8
    for rho_e in (0.0, 0.05, 0.2):
        # beta-binomial: each machine has its own accuracy p_g with Var(p_g) = rho_e * p * (1 - p)
        if rho_e == 0:
            p_g = np.full((2000, N_MACHINES), p)
        else:
            k = (1 - rho_e) / rho_e
            p_g = rng.beta(p * k, (1 - p) * k, (2000, N_MACHINES))
        acc = rng.binomial(m, p_g).sum(axis=1) / n
        naive = np.sqrt(p * (1 - p) / n)
        print(f"| {rho_e:.2f} | {naive:.4f} | {acc.std():.4f} | {(acc.std() / naive) ** 2:.1f} | {1 + (m - 1) * rho_e:.1f} |")


if __name__ == "__main__":
    main()
