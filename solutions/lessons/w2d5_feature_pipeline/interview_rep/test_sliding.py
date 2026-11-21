import random
import statistics

import pytest

from sliding import StreamingStats, sliding_max


@pytest.mark.parametrize("w", [1, 2, 5, 17])
def test_sliding_max_matches_brute_force(w):
    rng = random.Random(w)
    values = [rng.randint(-5, 5) for _ in range(200)]
    assert sliding_max(values, w) == [max(values[i - w + 1:i + 1]) for i in range(w - 1, len(values))]


def test_sliding_max_adversarial_orders():
    assert sliding_max(list(range(10, 0, -1)), 3) == list(range(10, 2, -1))   # decreasing: deque stays full
    assert sliding_max(list(range(10)), 3) == list(range(2, 10))              # increasing: deque of one
    assert sliding_max([7, 7, 7, 7], 2) == [7, 7, 7]                          # ties
    assert sliding_max([1, 2], 5) == []                                       # window longer than input


def test_streaming_stats_matches_recomputation():
    rng = random.Random(0)
    stats, seen = StreamingStats(8), []
    for _ in range(300):
        x = rng.gauss(3.0, 2.0)
        seen.append(x)
        mean, var = stats.update(x)
        window = seen[-8:]
        assert mean == pytest.approx(statistics.fmean(window))
        assert var == pytest.approx(statistics.pvariance(window), abs=1e-9)


def test_streaming_stats_large_offset_loses_precision_but_stays_non_negative():
    stats = StreamingStats(4)
    for x in [1e9 + d for d in (0.1, 0.2, 0.3, 0.4, 0.1, 0.2)]:
        _, var = stats.update(x)
        assert var >= 0.0
