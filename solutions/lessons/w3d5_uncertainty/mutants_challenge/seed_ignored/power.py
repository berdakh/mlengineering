"""Power of a paired comparison as a function of the number of independent test experiments."""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np

Draw = Callable[[np.random.Generator, int], np.ndarray]


def normal_draw(mean: float, sd: float) -> Draw:
    """Per-experiment differences drawn from N(mean, sd^2)."""
    return lambda rng, n: rng.normal(mean, sd, size=n)


def empirical_draw(pool: Sequence[float], shift: float = 0.0) -> Draw:
    """Per-experiment differences resampled with replacement from observed ones (plus a shift)."""
    pool = np.asarray(pool, dtype=float)
    return lambda rng, n: rng.choice(pool, size=n, replace=True) + shift


def power(draw: Draw, n_experiments: int, n_sim: int = 500, seed: int = 0,
          alpha: float = 0.05, n_perm: int = 499) -> float:
    """Fraction of simulated studies in which a two-sided sign-flip permutation test on the mean
    paired difference gives p <= alpha.

    Each simulated study draws ``n_experiments`` differences with ``draw(rng, n_experiments)``.
    The p-value is ``(1 + #{|permuted mean| >= |observed mean|}) / (1 + n_perm)``.
    """
    if n_experiments < 2:
        raise ValueError("need at least two experiments")
    rng = np.random.default_rng()                        # MUTANT: seed unused
    rejections = 0
    for _ in range(n_sim):
        d = np.asarray(draw(rng, n_experiments), dtype=float)
        observed = abs(d.mean())
        signs = rng.choice((1.0, -1.0), size=(n_perm, n_experiments))
        stats = np.abs(signs @ d) / n_experiments
        p = (1 + np.sum(stats >= observed - 1e-12)) / (1 + n_perm)
        rejections += p <= alpha
    return rejections / n_sim


def required_experiments(draw: Draw, candidates: Sequence[int], target_power: float = 0.8,
                         n_sim: int = 500, seed: int = 0, alpha: float = 0.05, n_perm: int = 499) -> int | None:
    """Smallest candidate n whose simulated power reaches ``target_power``; None if none does."""
    for n in sorted(candidates):
        if power(draw, n, n_sim=n_sim, seed=seed, alpha=alpha, n_perm=n_perm) >= target_power:
            return n
    return None
