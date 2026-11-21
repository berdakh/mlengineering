import random
import time

import pytest

from conftest import load


@pytest.fixture(scope="module")
def RollingStats():
    return load("p1").RollingStats


def test_rejects_non_positive_window(RollingStats):
    for bad in (0, -3):
        with pytest.raises(ValueError):
            RollingStats(bad)


def test_empty_raises(RollingStats):
    r = RollingStats(3)
    assert len(r) == 0
    with pytest.raises(ValueError):
        r.mean()
    with pytest.raises(ValueError):
        r.max()


def test_partial_window_uses_values_so_far(RollingStats):
    r = RollingStats(5)
    r.push(2.0)
    r.push(4.0)
    assert len(r) == 2
    assert r.mean() == pytest.approx(3.0)
    assert r.max() == 4.0


def test_oldest_value_leaves_exactly_at_window(RollingStats):
    r = RollingStats(3)
    for x in (9.0, 1.0, 2.0):
        r.push(x)
    assert (len(r), r.max(), r.mean()) == (3, 9.0, pytest.approx(4.0))
    r.push(3.0)                      # 9.0 leaves
    assert len(r) == 3
    assert r.max() == 3.0
    assert r.mean() == pytest.approx(2.0)


def test_window_of_one(RollingStats):
    r = RollingStats(1)
    for x in (5.0, -1.0, 7.5):
        r.push(x)
        assert (len(r), r.max(), r.mean()) == (1, x, pytest.approx(x))


def test_duplicates_of_the_maximum(RollingStats):
    r = RollingStats(2)
    for x in (4.0, 4.0, 1.0):
        r.push(x)                    # window is now (4.0, 1.0): one 4.0 must survive
    assert r.max() == 4.0
    r.push(0.0)                      # window (1.0, 0.0)
    assert r.max() == 1.0


@pytest.mark.parametrize("window", [1, 2, 7, 50])
def test_matches_brute_force_on_random_stream(RollingStats, window):
    rng = random.Random(window)
    r, held = RollingStats(window), []
    for _ in range(600):
        x = rng.choice([rng.uniform(-5, 5), float(rng.randint(-2, 2))])   # includes repeats
        r.push(x)
        held = (held + [x])[-window:]
        assert len(r) == len(held)
        assert r.max() == max(held)
        assert r.mean() == pytest.approx(sum(held) / len(held), abs=1e-9)


def test_amortised_constant_time(RollingStats):
    """300,000 pushes with window 20,000, querying after every push. A per-call scan of the window
    costs about 6e9 element visits and cannot finish in the budget; O(1) amortised takes well under a second."""
    rng = random.Random(0)
    data = [rng.random() for _ in range(300_000)]
    r = RollingStats(20_000)
    start = time.perf_counter()
    acc = 0.0
    for i, x in enumerate(data):
        r.push(x)
        acc += r.max() + r.mean()
        if i % 5_000 == 0 and time.perf_counter() - start > 5.0:
            pytest.fail(f"too slow: only {i:,} of {len(data):,} values processed in 5 s")
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, f"too slow: {elapsed:.1f} s"
    assert acc > 0
