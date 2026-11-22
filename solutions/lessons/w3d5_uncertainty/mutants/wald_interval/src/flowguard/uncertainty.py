"""Uncertainty for metrics whose independent unit is the experiment (the "cluster").

Vocabulary used throughout:

* ``per_experiment_results`` is a mapping ``{cluster_id: result}``. A *result* is whatever one
  cluster contributes: a dict of arrays, a DataFrame, a number. This module never looks inside it.
* ``metric_fn(results) -> float`` receives a **list of results** (one entry per drawn cluster,
  repeats included) and returns the metric for that pseudo-dataset. It may return NaN when the
  metric is undefined (for example recall when no drawn cluster has a positive).

Every interval here describes the variation from *which clusters happened to be in the evaluation
set*, with the fitted model held fixed. It says nothing about retraining or seed variation.
"""
from __future__ import annotations

import itertools
import math
from statistics import NormalDist
from typing import Any, Callable, Mapping

import numpy as np

MetricFn = Callable[[list], float]


def _check(n_boot: int, level: float) -> None:
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")


def _percentile_interval(replicates: np.ndarray, level: float) -> tuple[float, float, int]:
    finite = replicates[np.isfinite(replicates)]
    n_failed = int(len(replicates) - len(finite))
    if len(finite) == 0:
        return float("nan"), float("nan"), n_failed
    alpha = 1.0 - level
    low, high = np.quantile(finite, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(low), float(high), n_failed


def cluster_bootstrap(metric_fn: MetricFn, per_experiment_results: Mapping[Any, Any],
                      n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    """Percentile bootstrap interval, resampling whole clusters with replacement.

    Returns ``{"estimate", "low", "high", "level", "n_clusters", "n_boot", "n_failed"}``.
    ``estimate`` is ``metric_fn`` on the original clusters. Replicates for which ``metric_fn``
    returns NaN/inf are dropped from the percentiles and counted in ``n_failed``; if all fail,
    ``low`` and ``high`` are NaN. A large ``n_failed`` means the interval describes only the
    resamples where the metric existed, and should be reported.
    """
    _check(n_boot, level)
    results = list(per_experiment_results.values())
    n = len(results)
    if n < 2:
        raise ValueError("need at least two clusters to resample")
    rng = np.random.default_rng(seed)
    replicates = np.empty(n_boot)
    for b in range(n_boot):
        draw = rng.integers(0, n, size=n)
        replicates[b] = metric_fn([results[i] for i in draw])
    low, high, n_failed = _percentile_interval(replicates, level)
    return {"estimate": float(metric_fn(results)), "low": low, "high": high, "level": level,
            "n_clusters": n, "n_boot": n_boot, "n_failed": n_failed}


def paired_bootstrap_diff(metric_fn: MetricFn, results_a: Mapping[Any, Any], results_b: Mapping[Any, Any],
                          n_boot: int = 2000, seed: int = 0, level: float = 0.95) -> dict:
    """Interval for ``metric(A) - metric(B)`` when A and B were evaluated on the same clusters.

    One set of cluster indices is drawn per replicate and applied to **both** models, so the
    between-cluster difficulty that A and B share cancels in the difference.
    Raises ValueError if the two mappings do not have the same cluster ids.
    """
    _check(n_boot, level)
    if set(results_a) != set(results_b):
        raise ValueError("paired comparison needs the same cluster ids for both models")
    ids = list(results_a)
    n = len(ids)
    if n < 2:
        raise ValueError("need at least two clusters to resample")
    a = [results_a[i] for i in ids]
    b = [results_b[i] for i in ids]
    rng = np.random.default_rng(seed)
    replicates = np.empty(n_boot)
    for r in range(n_boot):
        draw = rng.integers(0, n, size=n)
        replicates[r] = metric_fn([a[i] for i in draw]) - metric_fn([b[i] for i in draw])
    low, high, n_failed = _percentile_interval(replicates, level)
    return {"estimate": float(metric_fn(a) - metric_fn(b)), "low": low, "high": high, "level": level,
            "n_clusters": n, "n_boot": n_boot, "n_failed": n_failed}


def wilson_interval(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion ``k / n``. Always inside [0, 1].

    ``n == 0`` returns ``(0.0, 1.0)``: no trials, no information.
    """
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    if n < 0 or k < 0 or k > n:
        raise ValueError("need 0 <= k <= n")
    if n == 0:
        return 0.0, 1.0
    z = NormalDist().inv_cdf(1.0 - (1.0 - level) / 2.0)
    p = k / n
    half = z * math.sqrt(p * (1.0 - p) / n)          # MUTANT: normal-approximation (Wald) interval
    return p - half, p + half


def sign_test(diffs) -> float:
    """Exact two-sided sign test on paired differences. Zeros are dropped; all zeros gives 1.0."""
    d = np.asarray(diffs, dtype=float)
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return 1.0
    k = int(min((d > 0).sum(), (d < 0).sum()))
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return float(min(1.0, 2.0 * tail))


def paired_permutation_test(diffs, n_perm: int = 9999, seed: int = 0) -> float:
    """Two-sided sign-flip permutation test of "mean paired difference is zero".

    Under the null hypothesis that the two models are exchangeable within each cluster, each
    difference is as likely to have had the opposite sign. With ``n <= 12`` clusters all ``2**n``
    sign patterns are enumerated (exact p-value). Otherwise ``n_perm`` random patterns are drawn and
    the p-value is ``(1 + #{|stat| >= |observed|}) / (1 + n_perm)``, which is never zero.
    """
    d = np.asarray(diffs, dtype=float)
    n = len(d)
    if n == 0:
        raise ValueError("no differences given")
    if n_perm < 1:
        raise ValueError("n_perm must be at least 1")
    observed = abs(d.mean())
    tol = 1e-12 * max(1.0, float(np.abs(d).max()))
    if n <= 12:
        signs = np.array(list(itertools.product((1.0, -1.0), repeat=n)))
        stats = np.abs(signs @ d) / n
        return float(np.mean(stats >= observed - tol))
    rng = np.random.default_rng(seed)
    signs = rng.choice((1.0, -1.0), size=(n_perm, n))
    stats = np.abs(signs @ d) / n
    return float((1 + np.sum(stats >= observed - tol)) / (1 + n_perm))
