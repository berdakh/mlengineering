"""Regenerate the figures of handbook section H6.6 (deterministic).

    python handbook/figures/h6_6/make_figures.py          # about 1 minute

design_effect.svg  pure formula: effective sample size of 1,200 rows as a function of the ICC.
power_curve.svg    simulation driven by REAL per-cluster PR-AUC differences on SKAB
                   (lessons/w3d5_uncertainty/challenge/per_cluster_pr_auc.csv), using the reference
                   power function of the w3d5 challenge. Numbers are printed and written to CSV.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "solutions" / "lessons" / "w3d5_uncertainty" / "challenge")]

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402


def fig_design_effect() -> None:
    icc = np.linspace(0.0, 1.0, 201)
    layouts = [(30, 40), (10, 120), (7, 171)]                    # (clusters, rows per cluster), about 1,200 rows
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    rows = []
    for colour, (g, m) in zip(SERIES, layouts):
        n_eff = g * m / (1.0 + (m - 1) * icc)
        ax.plot(icc, n_eff, color=colour, label=f"{g} clusters x {m} rows")
        ax.text(1.01, g, f"{g}", color=INK["secondary"], fontsize=9, va="center")
        for r in (0.0, 0.05, 0.1, 0.2, 0.5, 1.0):
            rows.append({"clusters": g, "rows_per_cluster": m, "icc": r, "n_eff": g * m / (1.0 + (m - 1) * r)})
    ax.set_yscale("log")
    ax.set_yticks([10, 30, 100, 300, 1000], ["10", "30", "100", "300", "1,000"])
    ax.set_xlabel("intraclass correlation (share of variance between clusters)")
    ax.set_ylabel("effective number of\nindependent observations")
    ax.legend(loc="upper right")
    ax.set_title("About 1,200 rows are worth far fewer; the floor is the number of clusters")
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "design_effect.csv", index=False)
    print(df.pivot(index="icc", columns="clusters", values="n_eff").round(1).to_string())
    save(fig, HERE / "design_effect.svg")


def fig_power_curve() -> None:
    from power import empirical_draw, power

    df = pd.read_csv(ROOT / "lessons" / "w3d5_uncertainty" / "challenge" / "per_cluster_pr_auc.csv")
    grid = [7, 10, 20, 30, 50, 100, 200, 400, 800, 1600]
    series = [("Mahalanobis vs flow-rate z", df["mahalanobis"] - df["flow_z"], SERIES[2]),
              ("supervised vs flow-rate z", df["logreg"] - df["flow_z"], SERIES[3])]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    out = []
    for name, d, colour in series:
        d = d.to_numpy()
        pw = [power(empirical_draw(d), n, n_sim=1000, seed=0) for n in grid]
        out += [{"comparison": name, "mean_diff": d.mean(), "sd_diff": d.std(ddof=1), "clusters": n, "power": p}
                for n, p in zip(grid, pw)]
        ax.plot(grid, pw, marker="o", color=colour, label=f"{name} (mean {d.mean():+.3f}, sd {d.std(ddof=1):.2f})")
    ax.axhline(0.8, color=INK["muted"], linestyle="--", linewidth=1)
    ax.text(7, 0.83, "80% power", fontsize=8, color=INK["muted"])
    ax.axvline(30, color=INK["axis"], linewidth=1)
    ax.text(31.5, 0.02, "30 clusters\navailable", fontsize=8, color=INK["muted"], va="bottom")
    ax.set_xscale("log")
    ax.set_xticks(grid, [str(g) for g in grid])
    ax.minorticks_off()
    ax.set_ylim(0, 1.03)
    ax.set_xlabel("independent test clusters (log scale)")
    ax.set_ylabel("probability of detecting the difference")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.2), ncols=1)
    ax.set_title("Real SKAB differences: a 0.03 PR-AUC gap needs hundreds of experiments")
    res = pd.DataFrame(out)
    res.to_csv(HERE / "power_curve.csv", index=False)
    print(res.pivot(index="clusters", columns="comparison", values="power").round(3).to_string())
    save(fig, HERE / "power_curve.svg")


if __name__ == "__main__":
    fig_design_effect()
    fig_power_curve()
