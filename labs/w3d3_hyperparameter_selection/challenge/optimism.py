"""Your simulation of the optimism of the maximum (challenge, w3d3)."""
from __future__ import annotations


def simulate_max(k: int, sigma: float, n_rep: int, seed: int, rho: float = 0.0) -> float:
    """Monte-Carlo mean of max(e_1, ..., e_k) over ``n_rep`` repetitions.

    The errors are zero-mean Gaussian with standard deviation ``sigma`` and equal pairwise
    correlation ``rho`` (0 = independent, 1 = one shared error). Same seed, same result.
    """
    raise NotImplementedError


if __name__ == "__main__":
    # Design your own experiment here: what do you vary, and what do you expect before you run it?
    pass
