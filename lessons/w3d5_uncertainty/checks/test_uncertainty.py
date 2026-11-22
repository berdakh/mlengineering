"""Behavioural checks for flowguard.uncertainty. Every dataset here is SYNTHETIC and seeded."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.stats import binomtest

KEYS = {"estimate", "low", "high", "level", "n_clusters", "n_boot", "n_failed"}


def pooled_mean(results) -> float:
    return float(np.mean(np.concatenate(results)))


def clustered(rng, n_clusters=30, rows=40, sd_cluster=1.0, sd_row=1.0) -> dict:
    """Rows share a cluster effect: intraclass correlation = sd_cluster^2 / (sd_cluster^2 + sd_row^2)."""
    return {f"c{i}": rng.normal(0.0, sd_cluster) + rng.normal(0.0, sd_row, size=rows) for i in range(n_clusters)}


# ------------------------------------------------------------------ cluster_bootstrap: contract
def test_returns_documented_keys_and_point_estimate(unc):
    data = clustered(np.random.default_rng(0), n_clusters=8, rows=5)
    out = unc.cluster_bootstrap(pooled_mean, data, n_boot=200, seed=1)
    assert KEYS <= set(out), f"missing keys: {KEYS - set(out)}"
    assert out["estimate"] == pytest.approx(pooled_mean(list(data.values())))
    assert out["low"] <= out["estimate"] <= out["high"]
    assert out["n_clusters"] == 8 and out["n_boot"] == 200 and out["n_failed"] == 0
    assert out["level"] == pytest.approx(0.95)


def test_clusters_are_never_split_or_altered(unc):
    """metric_fn must receive the ORIGINAL per-cluster objects: n_clusters of them, with repeats."""
    originals = {i: {"id": i, "rows": np.arange(5) + 10 * i} for i in range(6)}
    by_identity = {id(v) for v in originals.values()}
    seen_sizes, seen_multiset = set(), set()

    def metric(results):
        assert isinstance(results, list), "metric_fn must be called with a list of results"
        for r in results:
            assert id(r) in by_identity, "metric_fn received something that is not an original cluster result"
        seen_sizes.add(len(results))
        seen_multiset.add(tuple(sorted(r["id"] for r in results)))
        return float(np.mean([r["rows"].mean() for r in results]))

    unc.cluster_bootstrap(metric, originals, n_boot=150, seed=0)
    assert seen_sizes == {6}, f"each replicate must draw n_clusters clusters, saw sizes {seen_sizes}"
    assert any(len(set(m)) < 6 for m in seen_multiset), "sampling must be WITH replacement"
    assert len(seen_multiset) > 20, "replicates should differ from each other"


def test_same_seed_same_interval_different_seed_different(unc):
    data = clustered(np.random.default_rng(3), n_clusters=12, rows=10)
    a = unc.cluster_bootstrap(pooled_mean, data, n_boot=300, seed=11)
    b = unc.cluster_bootstrap(pooled_mean, data, n_boot=300, seed=11)
    c = unc.cluster_bootstrap(pooled_mean, data, n_boot=300, seed=12)
    assert (a["low"], a["high"]) == (b["low"], b["high"]), "same seed must reproduce the interval"
    assert (a["low"], a["high"]) != (c["low"], c["high"]), "the seed must actually drive the resampling"


def test_level_controls_width(unc):
    data = clustered(np.random.default_rng(4), n_clusters=20, rows=10)
    wide = unc.cluster_bootstrap(pooled_mean, data, n_boot=800, seed=0, level=0.95)
    narrow = unc.cluster_bootstrap(pooled_mean, data, n_boot=800, seed=0, level=0.50)
    assert (narrow["high"] - narrow["low"]) < 0.6 * (wide["high"] - wide["low"])


def test_coverage_is_near_nominal_under_within_cluster_dependence(unc):
    """Simulation: 30 clusters x 40 rows, intraclass correlation 0.5, true pooled mean 0.

    A 95% cluster-bootstrap interval should contain 0 in roughly 95% of repetitions (slightly
    fewer with 30 clusters). An interval that treats the 1,200 rows as independent is about 4.5
    times too narrow here and covers 0 in roughly a third of repetitions.
    """
    rng = np.random.default_rng(2026)
    reps, hits, widths = 150, 0, []
    for r in range(reps):
        out = unc.cluster_bootstrap(pooled_mean, clustered(rng), n_boot=200, seed=r)
        hits += out["low"] <= 0.0 <= out["high"]
        widths.append(out["high"] - out["low"])
    coverage = hits / reps
    assert coverage >= 0.86, (
        f"coverage {coverage:.2f} is far below the nominal 0.95: the interval is too narrow. "
        "Are whole clusters being resampled, or rows?")
    assert coverage <= 0.995, f"coverage {coverage:.2f}: the interval is implausibly wide"
    # true sd of the pooled mean = sqrt(1/30 + 1/1200) = 0.185; a 95% interval is about 3.92 sd wide
    assert 0.55 < float(np.median(widths)) < 0.90, f"median width {np.median(widths):.3f}, expected about 0.70"


def test_undefined_replicates_are_counted_not_fatal(unc):
    """Recall is undefined (NaN) when a resample draws no cluster with a positive."""
    data = {i: {"tp": 3 if i == 0 else 0, "pos": 4 if i == 0 else 0} for i in range(4)}

    def recall(results):
        pos = sum(r["pos"] for r in results)
        return float("nan") if pos == 0 else sum(r["tp"] for r in results) / pos

    out = unc.cluster_bootstrap(recall, data, n_boot=400, seed=0)
    assert out["estimate"] == pytest.approx(0.75)
    # P(no draw of cluster 0 in 4 draws) = (3/4)^4 = 0.316
    assert 70 <= out["n_failed"] <= 190, f"n_failed = {out['n_failed']}, expected about 127 of 400"
    assert math.isfinite(out["low"]) and math.isfinite(out["high"])
    assert out["low"] == pytest.approx(0.75) and out["high"] == pytest.approx(0.75)


def test_all_replicates_undefined_gives_nan_bounds(unc):
    out = unc.cluster_bootstrap(lambda results: float("nan"), {0: 1, 1: 2, 2: 3}, n_boot=20, seed=0)
    assert out["n_failed"] == 20 and math.isnan(out["low"]) and math.isnan(out["high"])


@pytest.mark.parametrize("kwargs", [{"n_boot": 0}, {"level": 1.0}, {"level": 0.0}])
def test_bad_arguments_raise(unc, kwargs):
    with pytest.raises(ValueError):
        unc.cluster_bootstrap(pooled_mean, {0: np.ones(3), 1: np.ones(3)}, **{"n_boot": 10, "seed": 0, **kwargs})


def test_a_single_cluster_cannot_be_resampled(unc):
    with pytest.raises(ValueError):
        unc.cluster_bootstrap(pooled_mean, {0: np.ones(3)}, n_boot=10, seed=0)


# ------------------------------------------------------------------ paired_bootstrap_diff
def planted_pair(n=12, shift=0.02):
    """Model A beats B by about `shift` on EVERY cluster; cluster difficulty varies far more."""
    rng = np.random.default_rng(7)
    difficulty = rng.normal(0.70, 0.15, size=n)
    b = {f"c{i}": float(difficulty[i]) for i in range(n)}
    a = {f"c{i}": float(difficulty[i] + shift + rng.normal(0.0, 0.004)) for i in range(n)}
    return a, b


def mean_of(results) -> float:
    return float(np.mean(results))


def test_paired_interval_detects_a_small_consistent_difference(unc):
    a, b = planted_pair()
    ci_a = unc.cluster_bootstrap(mean_of, a, n_boot=1000, seed=0)
    ci_b = unc.cluster_bootstrap(mean_of, b, n_boot=1000, seed=0)
    assert ci_a["low"] < ci_b["high"], "sanity: the two separate intervals overlap heavily"
    diff = unc.paired_bootstrap_diff(mean_of, a, b, n_boot=1000, seed=0)
    assert KEYS <= set(diff)
    assert diff["estimate"] == pytest.approx(mean_of(list(a.values())) - mean_of(list(b.values())))
    assert diff["low"] > 0.0, (
        f"paired interval [{diff['low']:.4f}, {diff['high']:.4f}] should exclude 0: A is better on every "
        "cluster. Draw ONE set of clusters per replicate and apply it to both models.")
    assert diff["high"] - diff["low"] < 0.02, "the paired interval should be far narrower than either separate one"


def test_paired_difference_of_identical_models_is_exactly_zero(unc):
    a, _ = planted_pair()
    diff = unc.paired_bootstrap_diff(mean_of, a, dict(a), n_boot=300, seed=5)
    assert diff["estimate"] == 0.0 and diff["low"] == 0.0 and diff["high"] == 0.0


def test_paired_pairs_by_cluster_id_not_by_position(unc):
    a, b = planted_pair()
    b_reordered = dict(reversed(list(b.items())))
    diff = unc.paired_bootstrap_diff(mean_of, a, b_reordered, n_boot=600, seed=0)
    assert diff["low"] > 0.0, "clusters must be matched by id even when the two mappings are ordered differently"


def test_paired_requires_the_same_clusters(unc):
    a, b = planted_pair()
    b.pop("c0")
    with pytest.raises(ValueError):
        unc.paired_bootstrap_diff(mean_of, a, b, n_boot=50, seed=0)


def test_paired_is_reproducible(unc):
    a, b = planted_pair()
    x = unc.paired_bootstrap_diff(mean_of, a, b, n_boot=200, seed=3)
    y = unc.paired_bootstrap_diff(mean_of, a, b, n_boot=200, seed=3)
    z = unc.paired_bootstrap_diff(mean_of, a, b, n_boot=200, seed=4)
    assert (x["low"], x["high"]) == (y["low"], y["high"]) != (z["low"], z["high"])


# ------------------------------------------------------------------ wilson_interval
@pytest.mark.parametrize("k,n", [(7, 9), (0, 9), (9, 9), (1, 9), (31, 34), (50, 100), (1, 1000)])
def test_wilson_matches_reference(unc, k, n):
    low, high = unc.wilson_interval(k, n)
    ref = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    assert low == pytest.approx(ref.low, abs=1e-6) and high == pytest.approx(ref.high, abs=1e-6)
    assert 0.0 <= low <= k / n <= high <= 1.0


def test_wilson_seven_of_nine_is_wide(unc):
    low, high = unc.wilson_interval(7, 9)
    assert low == pytest.approx(0.4526, abs=5e-4) and high == pytest.approx(0.9368, abs=5e-4)


def test_wilson_level_and_edge_cases(unc):
    l90, h90 = unc.wilson_interval(7, 9, level=0.90)
    l95, h95 = unc.wilson_interval(7, 9, level=0.95)
    assert l95 < l90 < h90 < h95
    assert unc.wilson_interval(0, 0) == (0.0, 1.0)
    for bad in [(-1, 5), (6, 5), (1, -1)]:
        with pytest.raises(ValueError):
            unc.wilson_interval(*bad)


# ------------------------------------------------------------------ tests on paired differences
def test_sign_test_known_values(unc):
    assert unc.sign_test([0.1] * 9 + [-0.1]) == pytest.approx(22 / 1024)
    assert unc.sign_test([0.3, -0.2, 0.1, -0.4]) == pytest.approx(1.0)
    assert unc.sign_test([0.0, 0.0]) == 1.0
    assert unc.sign_test([0.0] * 5 + [1.0] * 6) == pytest.approx(2 / 64), "zeros must be dropped"


def test_permutation_test_exact_small_sample(unc):
    # 10 equal positive differences: only the all-plus and all-minus patterns are as extreme.
    assert unc.paired_permutation_test([0.1] * 10) == pytest.approx(2 / 1024, rel=0.35)
    assert unc.paired_permutation_test([1, -1, 2, -2, 0.5, -0.5]) > 0.9


def test_permutation_test_uses_magnitudes_unlike_the_sign_test(unc):
    diffs = [0.30, 0.25, 0.28, 0.31, 0.27, 0.29, 0.26, -0.001, -0.002, -0.001]
    assert unc.sign_test(diffs) > 0.3
    assert unc.paired_permutation_test(diffs) < 0.05


def test_permutation_test_large_sample_never_zero_and_reproducible(unc):
    rng = np.random.default_rng(1)
    strong = rng.normal(1.0, 0.1, size=40)
    p = unc.paired_permutation_test(strong, n_perm=999, seed=0)
    assert 0.0 < p <= 0.002, f"p = {p}; with 999 random patterns the smallest possible p-value is 1/1000"
    null = rng.normal(0.0, 1.0, size=40)
    p1 = unc.paired_permutation_test(null, n_perm=999, seed=5)
    p2 = unc.paired_permutation_test(null, n_perm=999, seed=5)
    assert p1 == p2 and 0.0 < p1 <= 1.0


def test_permutation_test_is_calibrated_under_the_null(unc):
    """With no true difference, p <= 0.05 should happen about 5% of the time."""
    rng = np.random.default_rng(99)
    rejections = sum(unc.paired_permutation_test(rng.normal(0, 1, size=9)) <= 0.05 for _ in range(400))
    assert rejections / 400 <= 0.09, f"false-positive rate {rejections / 400:.3f} at alpha 0.05"
