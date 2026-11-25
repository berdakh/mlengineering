"""Worked example (SYNTHETIC): why an update gate must compare models on the SAME units, paired.

    python labs/w7d4_model_updates_rollback/example/paired_gate_demo.py

A demand-forecasting team replaces the model that flags stock-outs at 40 stores. Each store has its own
difficulty: some stock-outs are obvious, others are not. Generator (stated, nothing real):
* store difficulty d_s ~ Uniform(0.2, 0.9) = probability that the CURRENT model catches a stock-out;
* the candidate catches a stock-out with probability min(1, d_s + 0.06): a small, real improvement;
* each store has 6 stock-outs in the evaluation month; both models see the same ones.
Only numpy is used. The paired interval resamples stores once and applies the draw to both models;
the unpaired one resamples each model's stores independently.
"""
from __future__ import annotations

import numpy as np

rng = np.random.default_rng(11)
N_STORES, EVENTS = 40, 6
difficulty = rng.uniform(0.2, 0.9, N_STORES)
u = rng.random((N_STORES, EVENTS))                     # shared randomness: the same stock-outs
current = (u < difficulty[:, None]).sum(axis=1)        # caught per store
candidate = (u < np.minimum(1, difficulty + 0.06)[:, None]).sum(axis=1)


def recall(caught: np.ndarray) -> float:
    return caught.sum() / (EVENTS * len(caught))


def bootstrap(n_boot: int = 4000, paired: bool = True, seed: int = 0) -> tuple[float, float]:
    r = np.random.default_rng(seed)
    reps = np.empty(n_boot)
    for b in range(n_boot):
        i = r.integers(0, N_STORES, N_STORES)
        j = i if paired else r.integers(0, N_STORES, N_STORES)
        reps[b] = recall(candidate[i]) - recall(current[j])
    return tuple(np.quantile(reps, [0.025, 0.975]))


diff = recall(candidate) - recall(current)
print(f"recall: current {recall(current):.3f}, candidate {recall(candidate):.3f}, difference {diff:+.3f}")
print(f"stores where candidate caught more / fewer / same: {(candidate > current).sum()} / "
      f"{(candidate < current).sum()} / {(candidate == current).sum()}")
lo, hi = bootstrap(paired=True)
print(f"paired   95 % interval for the difference: [{lo:+.3f}, {hi:+.3f}]")
lo_u, hi_u = bootstrap(paired=False)
print(f"unpaired 95 % interval for the difference: [{lo_u:+.3f}, {hi_u:+.3f}]")
for policy, margin in (("superiority", 0.0), ("non-inferiority, margin 0.05", 0.05)):
    for name, low in (("paired", lo), ("unpaired", lo_u)):
        print(f"  {policy:<30} {name:<8}: {'PROMOTE' if low > -margin else 'reject'} (lower end {low:+.3f})")
