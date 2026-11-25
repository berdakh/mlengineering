"""Interview rep reference: paired cluster bootstrap for a difference in precision. SYNTHETIC demo.

    python solutions/labs/w3d5_uncertainty/interview_rep/paired_precision.py
"""
from __future__ import annotations

import numpy as np


def paired_precision_diff(y, pred_a, pred_b, machine, n_boot=2000, seed=0):
    """95% percentile interval for precision(B) - precision(A), resampling machines."""
    y, pred_a, pred_b, machine = map(np.asarray, (y, pred_a, pred_b, machine))
    ids = np.unique(machine)
    # per-machine sufficient statistics: TP and flagged counts for each model
    tp_a = np.array([np.sum((pred_a == 1) & (y == 1) & (machine == m)) for m in ids])
    fl_a = np.array([np.sum((pred_a == 1) & (machine == m)) for m in ids])
    tp_b = np.array([np.sum((pred_b == 1) & (y == 1) & (machine == m)) for m in ids])
    fl_b = np.array([np.sum((pred_b == 1) & (machine == m)) for m in ids])
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(ids), size=(n_boot, len(ids)))      # ONE draw, used for both models
    with np.errstate(invalid="ignore", divide="ignore"):
        diff = tp_b[draws].sum(1) / fl_b[draws].sum(1) - tp_a[draws].sum(1) / fl_a[draws].sum(1)
    diff = diff[np.isfinite(diff)]                                  # edge case: nothing flagged in a resample
    point = tp_b.sum() / fl_b.sum() - tp_a.sum() / fl_a.sum()
    return float(point), tuple(np.quantile(diff, [0.025, 0.975])), n_boot - len(diff)


def demo() -> None:
    rng = np.random.default_rng(1)
    n_machines, rows = 20, 2500
    machine = np.repeat(np.arange(n_machines), rows)
    y = (rng.random(machine.size) < 0.1).astype(int)
    fp_rate = rng.beta(2, 150, size=n_machines)                     # false-alarm rate differs by machine
    pred_a = np.where(y == 1, rng.random(y.size) < 0.80, rng.random(y.size) < fp_rate[machine]).astype(int)
    pred_b = np.where(y == 1, rng.random(y.size) < 0.80, rng.random(y.size) < 0.9 * fp_rate[machine]).astype(int)
    point, (low, high), failed = paired_precision_diff(y, pred_a, pred_b, machine)
    print(f"precision(B) - precision(A) = {point:+.4f}, machine-level paired 95% CI [{low:+.4f}, {high:+.4f}], "
          f"undefined replicates: {failed}")
    # the wrong answer for contrast: rows as the unit
    idx = rng.integers(0, y.size, size=(300, y.size))
    d = [(pred_b[i] & y[i]).sum() / pred_b[i].sum() - (pred_a[i] & y[i]).sum() / pred_a[i].sum() for i in idx]
    print(f"row-level paired 95% CI [{np.quantile(d, 0.025):+.4f}, {np.quantile(d, 0.975):+.4f}]")


if __name__ == "__main__":
    demo()
