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
    """Fraction of ``n_sim`` simulated studies in which the paired test rejects at level ``alpha``.

    See challenge/README.md for the exact test. Each simulated study obtains its per-experiment
    differences from ``draw(rng, n_experiments)``.
    """
    raise NotImplementedError


def required_experiments(draw: Draw, candidates: Sequence[int], target_power: float = 0.8,
                         n_sim: int = 500, seed: int = 0, alpha: float = 0.05, n_perm: int = 499) -> int | None:
    """Smallest candidate n whose simulated power reaches ``target_power``; None if none does."""
    raise NotImplementedError
