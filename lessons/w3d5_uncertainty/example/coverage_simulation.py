"""Worked example 1: does a "95% interval" contain the truth 95% of the time?

SYNTHETIC data. Rows inside a cluster share a random cluster effect, so they are dependent:

    y_ij = u_i + e_ij,   u_i ~ N(0, icc),   e_ij ~ N(0, 1 - icc)      (total variance 1, true mean 0)

For each setting we simulate many datasets, build a 95% percentile-bootstrap interval for the
pooled mean in two ways, and count how often the interval contains the true mean:

* row bootstrap     - rows resampled as if independent
* cluster bootstrap - whole clusters resampled

    python lessons/w3d5_uncertainty/example/coverage_simulation.py        # about 20 s

This shows the mechanics of dependence. It says nothing about SKAB or any real metric.
"""
from __future__ import annotations

import numpy as np

ROWS = 40
REPS = 1000
N_BOOT = 400


def simulate(rng, n_clusters: int, icc: float) -> np.ndarray:
    u = rng.normal(0.0, np.sqrt(icc), size=(n_clusters, 1))
    e = rng.normal(0.0, np.sqrt(1.0 - icc), size=(n_clusters, ROWS))
    return u + e


def row_interval(rng, y: np.ndarray) -> tuple[float, float]:
    flat = y.ravel()
    draws = rng.integers(0, flat.size, size=(N_BOOT, flat.size))
    return tuple(np.quantile(flat[draws].mean(axis=1), [0.025, 0.975]))


def cluster_interval(rng, y: np.ndarray) -> tuple[float, float]:
    cluster_means = y.mean(axis=1)                      # equal cluster sizes: pooled mean = mean of means
    draws = rng.integers(0, len(cluster_means), size=(N_BOOT, len(cluster_means)))
    return tuple(np.quantile(cluster_means[draws].mean(axis=1), [0.025, 0.975]))


def run(reps: int = REPS, seed: int = 0) -> list[dict]:
    """One dict per (clusters, ICC) setting with coverage and mean width of both intervals."""
    rng = np.random.default_rng(seed)
    rows = []
    for n_clusters in (30, 9, 7):
        for icc in (0.0, 0.1, 0.5):
            cover = {"row": 0, "cluster": 0}
            width = {"row": [], "cluster": []}
            for _ in range(reps):
                y = simulate(rng, n_clusters, icc)
                for name, fn in (("row", row_interval), ("cluster", cluster_interval)):
                    low, high = fn(rng, y)
                    cover[name] += low <= 0.0 <= high
                    width[name].append(high - low)
            rows.append({"clusters": n_clusters, "icc": icc, "design_effect": 1.0 + (ROWS - 1) * icc,
                         "row_coverage": cover["row"] / reps, "row_width": float(np.mean(width["row"])),
                         "cluster_coverage": cover["cluster"] / reps,
                         "cluster_width": float(np.mean(width["cluster"]))})
    return rows


def main() -> None:
    print(f"{REPS} simulated datasets per row, {ROWS} rows per cluster, nominal coverage 0.95\n")
    print("| clusters | ICC | design effect | row bootstrap: coverage (width) | cluster bootstrap: coverage (width) |")
    print("|---|---|---|---|---|")
    for r in run():
        print(f"| {r['clusters']} | {r['icc']:.1f} | {r['design_effect']:.1f} | "
              f"{r['row_coverage']:.3f} ({r['row_width']:.3f}) | "
              f"{r['cluster_coverage']:.3f} ({r['cluster_width']:.3f}) |")
    print("\nMonte Carlo standard error of each coverage figure: about 0.007 near 0.95, 0.015 near 0.5.")


if __name__ == "__main__":
    main()
