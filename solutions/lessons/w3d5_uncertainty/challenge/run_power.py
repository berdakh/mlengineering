"""Reference run of the power analysis on the real per-cluster differences.

    python solutions/lessons/w3d5_uncertainty/challenge/run_power.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from power import empirical_draw, normal_draw, power, required_experiments  # noqa: E402

CSV = HERE.parents[3] / "lessons" / "w3d5_uncertainty" / "challenge" / "per_cluster_pr_auc.csv"
GRID = [10, 20, 30, 50, 100, 200, 400, 800, 1600]

df = pd.read_csv(CSV)
print("| comparison | mean diff | sd | clusters | power at 7 | power at 30 | n for 80% power (empirical) | n for 80% (normal, same mean/sd) |")
print("|---|---|---|---|---|---|---|---|")
for name, col in [("logreg - flow_z", "logreg"), ("mahalanobis - flow_z", "mahalanobis")]:
    d = (df[col] - df["flow_z"]).to_numpy()
    emp = empirical_draw(d)
    nrm = normal_draw(d.mean(), d.std(ddof=1))
    row = [name, f"{d.mean():+.4f}", f"{d.std(ddof=1):.4f}", str(len(d)),
           f"{power(emp, 7, n_sim=2000, seed=0):.3f}", f"{power(emp, 30, n_sim=2000, seed=0):.3f}",
           str(required_experiments(emp, GRID, n_sim=1000, seed=0)),
           str(required_experiments(nrm, GRID, n_sim=1000, seed=0))]
    print("| " + " | ".join(row) + " |")

print("\nSmallest mean difference detectable with 80% power (normal differences, sd as observed for logreg - flow_z):")
sd = float((df["logreg"] - df["flow_z"]).std(ddof=1))
for n in (7, 9, 30, 34):
    for delta in np.arange(0.02, 0.60, 0.01):
        if power(normal_draw(delta, sd), n, n_sim=600, seed=0) >= 0.8:
            print(f"  n = {n:>2}: about {delta:.2f} PR-AUC")
            break
