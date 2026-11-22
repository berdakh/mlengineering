"""Reference solution: Monte-Carlo estimate of the optimism of the maximum."""
from __future__ import annotations

import math

import numpy as np


def simulate_max(k: int, sigma: float, n_rep: int, seed: int, rho: float = 0.0) -> float:
    """Mean of max(e_1..e_k) for zero-mean Gaussian errors with s.d. ``sigma`` and pairwise correlation ``rho``."""
    if k < 1 or sigma < 0 or not 0.0 <= rho <= 1.0:
        raise ValueError("need k >= 1, sigma >= 0 and 0 <= rho <= 1")
    rng = np.random.default_rng(seed)
    shared = rng.standard_normal((n_rep, 1))
    own = rng.standard_normal((n_rep, k))
    errors = sigma * (math.sqrt(rho) * shared + math.sqrt(1.0 - rho) * own)
    return float(errors.max(axis=1).mean())


if __name__ == "__main__":
    print(" K   rho   simulated   sigma*sqrt(2 ln K)")
    for k in (5, 20, 60, 200):
        for rho in (0.0, 0.5, 0.9):
            print(f"{k:3d}  {rho:.1f}   {simulate_max(k, 0.02, 40_000, 0, rho):.4f}      {0.02 * math.sqrt(2 * math.log(k)):.4f}")
