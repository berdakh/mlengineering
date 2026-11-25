"""Arithmetic checks for the estimation worksheet.

Each estimate is compared with the formula it states, over many randomly drawn (seeded) inputs, so a
hard-coded answer or a unit slip (per hour instead of per second, a missing factor) fails. The tests do
not care how the function is written, only what it returns.
"""
from __future__ import annotations

import math
import random

import pytest

RNG = random.Random(8053)
CASES = 40


def _close(a, b, rel=1e-9):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


def test_peak_qps_matches_definition(est):
    for _ in range(CASES):
        per_day = RNG.uniform(1e3, 1e9)
        ratio = RNG.uniform(1, 20)
        assert _close(est.peak_qps(per_day, ratio), per_day / 86_400 * ratio)


def test_peak_qps_known_value(est):
    # 8.64 million requests a day is 100 per second on average.
    assert _close(est.peak_qps(8_640_000, 3), 300.0)


@pytest.mark.parametrize("args", [(0, 2), (-5, 2), (1000, 0.5), (1000, float("nan"))])
def test_peak_qps_rejects_meaningless_input(est, args):
    with pytest.raises(ValueError):
        est.peak_qps(*args)


def test_storage_scales_with_every_factor(est):
    for _ in range(CASES):
        e, b, r, k = RNG.uniform(1, 1e8), RNG.uniform(1, 1e5), RNG.uniform(1, 400), RNG.randint(1, 5)
        assert _close(est.storage_bytes(e, b, r, k), e * b * r * k)
    assert _close(est.storage_bytes(1e6, 2_000, 90), 1.8e11)  # replication defaults to 1


@pytest.mark.parametrize("args", [(1e6, 100, 30, 0), (1e6, 100, 30, 1.5), (1e6, 0, 30, 1)])
def test_storage_rejects_bad_input(est, args):
    with pytest.raises(ValueError):
        est.storage_bytes(*args)


def test_labels_available_respects_delay(est):
    for _ in range(CASES):
        per_day = RNG.uniform(10, 1e6)
        rate = RNG.uniform(0.001, 1.0)
        delay = RNG.uniform(0, 60)
        window = RNG.uniform(1, 120)
        expected = per_day * rate * max(0.0, window - delay)
        assert _close(est.labels_available(per_day, rate, delay, window), expected)


def test_labels_available_zero_when_window_shorter_than_delay(est):
    assert est.labels_available(10_000, 0.5, 30, 14) == 0


@pytest.mark.parametrize("args", [(100, 0, 1, 10), (100, 1.2, 1, 10), (100, 0.5, -1, 10), (100, 0.5, 1, 0)])
def test_labels_available_rejects_bad_input(est, args):
    with pytest.raises(ValueError):
        est.labels_available(*args)


def test_latency_remaining(est):
    for _ in range(CASES):
        budget = RNG.uniform(10, 2_000)
        parts = {f"c{i}": RNG.uniform(0, 200) for i in range(RNG.randint(0, 6))}
        assert _close(est.latency_remaining_ms(budget, parts), budget - sum(parts.values()))
    assert est.latency_remaining_ms(100, {"a": 80, "b": 50}) == -30  # over budget is reported, not hidden


def test_latency_rejects_negative_component(est):
    with pytest.raises(ValueError):
        est.latency_remaining_ms(100, {"a": -5})


def test_replicas_is_little_law_rounded_up(est):
    for _ in range(CASES):
        qps = RNG.uniform(0.5, 5_000)
        ms = RNG.uniform(0.5, 500)
        cores = RNG.randint(1, 16)
        util = RNG.uniform(0.3, 0.95)
        expected = max(1, math.ceil(qps * ms / 1000 / (cores * util) - 1e-12))
        assert est.replicas_needed(qps, ms, cores, util) == expected


def test_replicas_exact_boundary_and_minimum(est):
    # 100 req/s x 20 ms = 2 busy cores; 1 core per replica at 100 % -> exactly 2, not 3.
    assert est.replicas_needed(100, 20, 1, 1.0) == 2
    assert est.replicas_needed(100, 21, 1, 1.0) == 3  # never round down: 2.1 busy cores need 3
    assert est.replicas_needed(0.1, 1, 4, 0.5) == 1   # at least one replica


def test_labels_for_precision(est):
    for _ in range(CASES):
        p = RNG.uniform(0.01, 0.99)
        hw = RNG.uniform(0.005, 0.2)
        z = RNG.choice([1.645, 1.96, 2.576])
        assert est.labels_for_precision(p, hw, z) == math.ceil(z * z * p * (1 - p) / hw ** 2 - 1e-12)
    # Halving the half-width needs four times the labels (up to rounding).
    a, b = est.labels_for_precision(0.5, 0.04), est.labels_for_precision(0.5, 0.02)
    assert 3.9 <= b / a <= 4.1


@pytest.mark.parametrize("args", [(0, 0.05), (1.0, 0.05), (0.5, 0), (0.5, 0.6)])
def test_labels_for_precision_rejects_bad_input(est, args):
    with pytest.raises(ValueError):
        est.labels_for_precision(*args)
