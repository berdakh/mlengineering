"""extract_events: runs of ones as half-open (start, end) pairs, then merge, then minimum duration."""
import numpy as np
import pytest


def as_pairs(events):
    return [(int(s), int(e)) for s, e in events]


@pytest.mark.parametrize("binary, expected", [
    ([], []),
    ([0, 0, 0], []),
    ([1, 1, 1], [(0, 3)]),
    ([1, 1, 0, 0, 1], [(0, 2), (4, 5)]),          # events touching both ends of the array
    ([0, 1, 0, 1, 0], [(1, 2), (3, 4)]),          # two events separated by a single normal row
    ([0, 0, 1], [(2, 3)]),
])
def test_known_answers(ev, binary, expected):
    assert as_pairs(ev.extract_events(binary)) == expected


def test_accepts_bool_and_numpy_input(ev):
    assert as_pairs(ev.extract_events(np.array([False, True, True, False]))) == [(1, 3)]


@pytest.mark.parametrize("seed", range(5))
def test_events_reconstruct_the_input_exactly(ev, seed):
    rng = np.random.default_rng(seed)
    binary = (rng.random(300) < 0.4).astype(int)
    events = as_pairs(ev.extract_events(binary))
    rebuilt = np.zeros_like(binary)
    for s, e in events:
        assert e > s, "an event must contain at least one row"
        rebuilt[s:e] = 1                              # end is exclusive
    assert np.array_equal(rebuilt, binary), "events (start, end) with end exclusive must rebuild the flags"
    assert sum(e - s for s, e in events) == int(binary.sum()), "event lengths must add up to the number of ones"
    assert events == sorted(events)


def test_merge_gap(ev):
    assert as_pairs(ev.extract_events([1, 0, 1])) == [(0, 1), (2, 3)]
    assert as_pairs(ev.extract_events([1, 0, 1], merge_gap=1)) == [(0, 3)]
    assert as_pairs(ev.extract_events([1, 0, 0, 1], merge_gap=1)) == [(0, 1), (3, 4)]
    assert as_pairs(ev.extract_events([1, 0, 0, 1], merge_gap=2)) == [(0, 4)]


def test_min_duration(ev):
    binary = [1, 0, 1, 1, 0, 1, 1, 1]
    assert as_pairs(ev.extract_events(binary, min_duration=2)) == [(2, 4), (5, 8)]
    assert as_pairs(ev.extract_events(binary, min_duration=3)) == [(5, 8)]
    assert as_pairs(ev.extract_events(binary, min_duration=4)) == []


def test_merging_happens_before_the_duration_filter(ev):
    # a chattering alarm: three 1-row bursts one row apart, then an isolated flag far away
    binary = [1, 0, 1, 0, 1, 0, 0, 0, 0, 1]
    assert as_pairs(ev.extract_events(binary, min_duration=3, merge_gap=1)) == [(0, 5)]


def test_invalid_parameters_are_rejected(ev):
    with pytest.raises(ValueError):
        ev.extract_events([0, 1], min_duration=0)
    with pytest.raises(ValueError):
        ev.extract_events([0, 1], merge_gap=-1)


def test_scaling_scores_and_threshold_together_changes_nothing(ev):
    rng = np.random.default_rng(1)
    scores, threshold = rng.random(500), 0.7
    base = as_pairs(ev.extract_events(scores >= threshold))
    assert as_pairs(ev.extract_events(1000.0 * scores >= 1000.0 * threshold)) == base
