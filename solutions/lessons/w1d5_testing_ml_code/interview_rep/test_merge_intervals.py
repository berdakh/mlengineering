import random

import pytest

from merge_intervals import merge_intervals


@pytest.mark.parametrize("intervals, expected", [
    ([], []),
    ([(1, 3)], [(1, 3)]),
    ([(1, 3), (5, 7)], [(1, 3), (5, 7)]),            # disjoint
    ([(1, 3), (2, 6)], [(1, 6)]),                    # overlap
    ([(1, 3), (3, 5)], [(1, 5)]),                    # touching -> merged (spec)
    ([(1, 3), (4, 5)], [(1, 3), (4, 5)]),            # gap of one -> not merged
    ([(1, 10), (2, 3)], [(1, 10)]),                  # containment: stop must be the max
    ([(5, 7), (1, 3), (2, 6)], [(1, 7)]),            # unsorted, chained
    ([(1, 3), (1, 3)], [(1, 3)]),                    # duplicates
])
def test_merge_intervals_cases(intervals, expected):
    assert merge_intervals(intervals) == expected


def test_input_not_modified():
    intervals = [(5, 7), (1, 3)]
    merge_intervals(intervals)
    assert intervals == [(5, 7), (1, 3)]


def test_reversed_interval_rejected():
    with pytest.raises(ValueError):
        merge_intervals([(3, 1)])


def test_properties_on_random_input():
    rng = random.Random(0)
    for _ in range(200):
        intervals = [(a, a + rng.randint(1, 5)) for a in (rng.randint(0, 40) for _ in range(rng.randint(0, 8)))]
        out = merge_intervals(intervals)
        assert out == sorted(out)
        assert all(a[1] < b[0] for a, b in zip(out, out[1:]))             # disjoint and not touching
        covered_in = {i for s, e in intervals for i in range(s, e)}
        covered_out = {i for s, e in out for i in range(s, e)}
        assert covered_in == covered_out                                   # nothing gained, nothing lost
