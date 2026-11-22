import random

from intervals import merge_intervals, overlap_length


def brute(a, b):
    cover = lambda xs: {t for s, e in xs for t in range(s, e)}  # noqa: E731
    return len(cover(a) & cover(b))


def test_merge_basic():
    assert merge_intervals([(5, 8), (1, 3), (2, 4)]) == [(1, 4), (5, 8)]


def test_merge_touching_nested_empty_and_duplicates():
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]
    assert merge_intervals([(1, 10), (2, 3), (4, 5)]) == [(1, 10)]
    assert merge_intervals([(4, 4), (7, 2)]) == []
    assert merge_intervals([(1, 2), (1, 2)]) == [(1, 2)]
    assert merge_intervals([]) == []


def test_merge_does_not_mutate_input():
    data = [(3, 6), (1, 4)]
    merge_intervals(data)
    assert data == [(3, 6), (1, 4)]


def test_overlap_known():
    assert overlap_length([(0, 10)], [(5, 15)]) == 5
    assert overlap_length([(0, 5)], [(5, 9)]) == 0
    assert overlap_length([(0, 4), (2, 6)], [(1, 3), (5, 8)]) == 3      # overlapping inputs are not double counted
    assert overlap_length([], [(1, 2)]) == 0


def test_overlap_matches_brute_force():
    rng = random.Random(0)
    for _ in range(200):
        make = lambda: [(s, s + rng.randint(0, 6)) for s in (rng.randint(0, 40) for _ in range(rng.randint(0, 6)))]  # noqa: E731
        a, b = make(), make()
        assert overlap_length(a, b) == brute(a, b)
