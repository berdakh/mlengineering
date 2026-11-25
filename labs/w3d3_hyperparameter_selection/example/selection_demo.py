"""Worked example: what selecting the best of K noisy estimates does to the number you report.

    python labs/w3d3_hyperparameter_selection/example/selection_demo.py

Everything here is a SYNTHETIC simulation with NumPy only. It shows mechanisms; it says nothing
about any particular dataset. Four parts:

  A. the optimism of the maximum when all K candidates are equally good;
  B. the same when the K estimates share noise (the usual case: same folds for every candidate);
  C. the winner's curse when candidates really differ: the winner is good AND lucky;
  D. grid versus random search when only one of two hyperparameters matters.
"""
from __future__ import annotations

import math

import numpy as np

SIGMA = 0.02      # standard error of one cross-validated estimate (e.g. PR-AUC over 4 folds)
TRUE = 0.70       # true performance of every candidate in parts A and B
REPS = 20_000


def max_of_k(k: int, sigma: float, reps: int, rng, rho: float = 0.0) -> float:
    """Mean over ``reps`` of max_i(estimate_i - truth), estimates equicorrelated with correlation rho."""
    shared = rng.standard_normal((reps, 1))
    own = rng.standard_normal((reps, k))
    noise = sigma * (math.sqrt(rho) * shared + math.sqrt(1.0 - rho) * own)
    return float(noise.max(axis=1).mean())


def part_a_b(rng) -> list[dict]:
    rows = []
    for k in (1, 2, 5, 10, 20, 50, 100, 500):
        rows.append({"K": k,
                     "independent": max_of_k(k, SIGMA, REPS, rng),
                     "rho_0.7": max_of_k(k, SIGMA, REPS, rng, rho=0.7),
                     "bound": SIGMA * math.sqrt(2.0 * math.log(k)) if k > 1 else 0.0})
    return rows


def part_c(rng, k: int = 60, spread: float = 0.01, reps: int = REPS) -> dict:
    """Candidates differ: true quality ~ N(TRUE, spread^2). Select by noisy dev estimate."""
    truth = TRUE + spread * rng.standard_normal((reps, k))
    dev = truth + SIGMA * rng.standard_normal((reps, k))
    pick = dev.argmax(axis=1)
    rows = np.arange(reps)
    return {"dev_of_winner": float(dev[rows, pick].mean()),
            "truth_of_winner": float(truth[rows, pick].mean()),
            "truth_of_best": float(truth.max(axis=1).mean()),
            "truth_of_random": float(truth[:, 0].mean()),
            "p_winner_is_truly_best": float(np.mean(pick == truth.argmax(axis=1)))}


def response(log10_c: np.ndarray, depth: np.ndarray) -> np.ndarray:
    """A validation score that depends sharply on C (peak at 10^-0.6) and not at all on depth."""
    return 0.80 - 0.05 * (log10_c + 0.6) ** 2 + 0.0 * depth


def part_d(rng, budget: int = 16, reps: int = 5000) -> dict:
    side = int(math.sqrt(budget))
    grid_c = np.linspace(-3, 3, side)                                # 4 distinct values of the important one
    grid_best = float(response(np.repeat(grid_c, side), np.tile(np.arange(side), side)).max())
    random_best = response(rng.uniform(-3, 3, (reps, budget)), rng.integers(1, 9, (reps, budget))).max(axis=1)
    return {"budget": budget, "optimum": 0.80, "grid_distinct_C": side, "random_distinct_C": budget,
            "grid_best": grid_best, "random_best_mean": float(random_best.mean()),
            "random_beats_grid": float(np.mean(random_best > grid_best))}


def main() -> None:
    rng = np.random.default_rng(0)
    print(f"A/B. All K candidates have true score {TRUE:.2f}; each estimate has standard error {SIGMA}.")
    print("     Mean amount by which the BEST estimate exceeds the truth:")
    print("        K   independent   correlated(rho=0.7)   sigma*sqrt(2 ln K)")
    for r in part_a_b(rng):
        print(f"     {r['K']:4d}      {r['independent']:.4f}          {r['rho_0.7']:.4f}              {r['bound']:.4f}")
    c = part_c(rng)
    print("\nC. 60 candidates whose true scores differ (s.d. 0.01), selected by a dev estimate with s.e. 0.02:")
    print(f"     dev estimate of the winner   {c['dev_of_winner']:.4f}")
    print(f"     true score of the winner     {c['truth_of_winner']:.4f}   (optimism {c['dev_of_winner'] - c['truth_of_winner']:.4f})")
    print(f"     true score of the true best  {c['truth_of_best']:.4f}   (regret   {c['truth_of_best'] - c['truth_of_winner']:.4f})")
    print(f"     true score of a random one   {c['truth_of_random']:.4f}")
    print(f"     the winner is the truly best candidate in {c['p_winner_is_truly_best']:.1%} of repetitions")
    d = part_d(rng)
    print(f"\nD. Budget {d['budget']} trials, score depends only on C (optimum {d['optimum']:.3f}):")
    print(f"     4x4 grid:  {d['grid_distinct_C']} distinct values of C, best score found {d['grid_best']:.4f}")
    print(f"     random:   {d['random_distinct_C']} distinct values of C, best score found {d['random_best_mean']:.4f} on average; "
          f"beats the grid in {d['random_beats_grid']:.1%} of runs")


if __name__ == "__main__":
    main()
