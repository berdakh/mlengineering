"""C3: statistics over a time-based trailing window with irregular timestamps."""
import math
import random
import statistics
import time

import pytest


def brute(history, now, horizon):
    xs = [x for t, x in history if now - horizon < t <= now]
    mean = sum(xs) / len(xs)
    std = statistics.stdev(xs) if len(xs) >= 2 else float("nan")
    return len(xs), mean, std



def test_gap_empties_the_window(c3):
    s = c3.TimeWindowStats(horizon_s=60)
    for t in range(0, 50):
        s.push(float(t), 10.0)
    s.push(300.0, 99.0)          # a 250 s gap: nothing older than 240 s may remain
    assert len(s) == 1
    assert s.mean() == pytest.approx(99.0)
    assert math.isnan(s.std())   # one value: sample standard deviation undefined


def test_boundary_is_half_open(c3):
    s = c3.TimeWindowStats(horizon_s=10)
    s.push(0.0, 1.0)
    s.push(5.0, 2.0)
    s.push(10.0, 3.0)            # window is (0, 10]: the value at t=0 has left
    assert len(s) == 2
    assert s.mean() == pytest.approx(2.5)


@pytest.mark.parametrize("seed", range(6))
def test_matches_brute_force_on_irregular_streams(c3, seed):
    rng = random.Random(seed)
    horizon = rng.choice([5.0, 30.0, 60.0])
    s = c3.TimeWindowStats(horizon_s=horizon)
    t, history = 0.0, []
    for _ in range(400):
        t += rng.choice([1.0, 1.0, 1.0, 2.0, 0.5, 40.0 if rng.random() < 0.03 else 1.0])
        x = rng.gauss(50.0, 5.0)
        history.append((t, x))
        s.push(t, x)
        n, mean, std = brute(history, t, horizon)
        assert len(s) == n
        assert s.mean() == pytest.approx(mean, rel=1e-9, abs=1e-9)
        if n >= 2:
            assert s.std() == pytest.approx(std, rel=1e-6, abs=1e-6)
        else:
            assert math.isnan(s.std())


def test_sample_standard_deviation_known_answer(c3):
    s = c3.TimeWindowStats(horizon_s=100)
    for t, x in enumerate([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]):
        s.push(float(t), x)
    assert s.mean() == pytest.approx(5.0)
    assert s.std() == pytest.approx(math.sqrt(32.0 / 7.0))     # n-1 in the denominator


def test_constant_signal_with_large_offset_has_zero_std_not_nan_or_negative(c3):
    s = c3.TimeWindowStats(horizon_s=50)
    for t in range(500):
        s.push(float(t), 1e6 + 0.1)
    assert s.std() == pytest.approx(0.0, abs=1e-3)             # never sqrt of a negative number


def test_errors(c3):
    with pytest.raises(ValueError):
        c3.TimeWindowStats(horizon_s=0)
    s = c3.TimeWindowStats(horizon_s=10)
    with pytest.raises(ValueError):
        s.mean()
    s.push(5.0, 1.0)
    with pytest.raises(ValueError):
        s.push(4.0, 1.0)                                       # time must not go backwards
    s.push(5.0, 2.0)                                           # equal timestamps are allowed
    assert len(s) == 2


def test_amortised_constant_time(c3):
    s = c3.TimeWindowStats(horizon_s=20_000)
    start = time.perf_counter()
    total = 0.0
    for t in range(200_000):                                   # window holds 20,000 values
        s.push(float(t), float(t % 97))
        total += s.mean() + s.std()
        if t % 1000 == 0 and time.perf_counter() - start > 5.0:
            pytest.fail(f"over 5 s after {t} of 200,000 pushes: statistics are probably "
                        "recomputed over the window on every call")
    assert time.perf_counter() - start < 5.0
