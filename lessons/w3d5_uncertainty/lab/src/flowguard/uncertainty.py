"""Uncertainty for metrics whose independent unit is the experiment (the "cluster").

YOUR TASK (w3d5 lab): implement the five functions below. Signatures, return keys and documented
behaviour are the contract that `python wb.py check w3d5` grades; everything else is up to you.

Vocabulary:

* ``per_experiment_results`` is a mapping ``{cluster_id: result}``. A *result* is whatever one
  cluster contributes: a dict of arrays, a DataFrame, a number. Do not look inside it.
* ``metric_fn(results) -> float`` receives a **list of results** (one entry per drawn cluster,
  repeats included) and returns the metric for that pseudo-dataset. It may return NaN when the
  metric is undefined (for example recall when no drawn cluster has a positive).
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

MetricFn = Callable[[list], float]


def cluster_bootstrap(metric_fn: MetricFn, per_experiment_results: Mapping[Any, Any],
                      n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    """Percentile bootstrap interval, resampling whole clusters with replacement.

    Return ``{"estimate", "low", "high", "level", "n_clusters", "n_boot", "n_failed"}``.

    * ``estimate`` is ``metric_fn`` on the original clusters (each exactly once).
    * Each replicate draws ``n_clusters`` clusters with replacement and passes the drawn results,
      unmodified, to ``metric_fn``.
    * Replicates where ``metric_fn`` returns NaN are left out of the percentiles and counted in
      ``n_failed``; if every replicate fails, ``low`` and ``high`` are NaN.
    * Same ``seed`` gives the same interval; a different seed gives a (slightly) different one.
    * ValueError for ``n_boot < 1``, ``level`` outside (0, 1), or fewer than two clusters.
    """
    raise NotImplementedError


def paired_bootstrap_diff(metric_fn: MetricFn, results_a: Mapping[Any, Any], results_b: Mapping[Any, Any],
                          n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    """Interval for ``metric(A) - metric(B)`` when A and B were evaluated on the same clusters.

    Same return keys as ``cluster_bootstrap``; ``estimate`` is the difference on the original data.
    ValueError if the two mappings do not have the same cluster ids.
    """
    raise NotImplementedError


def wilson_interval(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Wilson score interval ``(low, high)`` for a binomial proportion ``k / n``.

    Always inside [0, 1]. ``n == 0`` returns ``(0.0, 1.0)``. ValueError unless ``0 <= k <= n``.
    """
    raise NotImplementedError


def sign_test(diffs) -> float:
    """Exact two-sided sign test p-value on paired differences. Zeros are dropped; all zeros gives 1.0."""
    raise NotImplementedError


def paired_permutation_test(diffs, n_perm: int = 9999, seed: int = 0) -> float:
    """Two-sided sign-flip permutation p-value for "the mean paired difference is zero".

    The p-value is never 0: either enumerate all ``2**n`` sign patterns (the observed one is among
    them) or use ``(1 + count) / (1 + n_perm)`` for random patterns. Same seed, same p-value.
    """
    raise NotImplementedError
