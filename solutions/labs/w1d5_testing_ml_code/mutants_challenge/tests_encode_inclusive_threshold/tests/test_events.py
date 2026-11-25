"""Reference tests for detect_events, derived from the specification only.

Structure: one boundary per test. Each clause of the spec that contains a
comparison (>, >=, <=, half-open) gets a case sitting exactly ON the boundary.
"""
import numpy as np
import pytest

from eventkit.events import detect_events


def events(score, **kwargs):
    return [(int(a), int(b)) for a, b in detect_events(score, **kwargs)]


# ---- runs and their boundaries -------------------------------------------------------

@pytest.mark.parametrize("score, expected", [
    ([0, 0, 5, 5, 5, 0, 0], [(2, 5)]),          # interior event, stop is exclusive
    ([5, 5, 0, 0], [(0, 2)]),                   # event touching the start
    ([0, 0, 5, 5], [(2, 4)]),                   # event still open at the end
    ([5, 5, 5], [(0, 3)]),                      # everything above
    ([0, 0, 0], []),                            # nothing above
    ([], []),                                   # empty input
    ([5, 0, 5, 0, 5], [(0, 1), (2, 3), (4, 5)]),  # single-sample events, default min_samples=1
])
def test_runs(score, expected):
    assert events(score, threshold=1) == expected


def test_threshold_is_strict():
    assert events([1.0, 1.0, 1.0], threshold=1.0) == [(0, 3)]
    assert events([1.0, 1.0 + 1e-9, 1.0], threshold=1.0) == [(1, 2)]


def test_nan_is_never_above_and_splits_events():
    assert events([5, np.nan, 5, 5], threshold=1) == [(0, 1), (2, 4)]
    assert events([np.nan, np.nan], threshold=-1e9) == []


# ---- min_samples ---------------------------------------------------------------------

def test_min_samples_boundary_is_inclusive():
    score = [0, 5, 5, 5, 0, 5, 5, 0]             # runs of length 3 and 2
    assert events(score, threshold=1, min_samples=3) == [(1, 4)]
    assert events(score, threshold=1, min_samples=2) == [(1, 4), (5, 7)]
    assert events(score, threshold=1, min_samples=4) == []


# ---- merging -------------------------------------------------------------------------

def test_merge_gap_boundary_is_inclusive():
    score = [5, 5, 0, 0, 5, 5]                   # gap of exactly 2 samples
    assert events(score, threshold=1, merge_gap=1) == [(0, 2), (4, 6)]
    assert events(score, threshold=1, merge_gap=2) == [(0, 6)]


def test_merge_gap_zero_never_merges():
    assert events([5, 0, 5], threshold=1, merge_gap=0) == [(0, 1), (2, 3)]


def test_merging_chains_across_several_runs():
    assert events([5, 0, 5, 0, 5, 0, 0, 0, 5], threshold=1, merge_gap=1) == [(0, 5), (8, 9)]


def test_merge_happens_before_duration_filter():
    # Three 1-sample fragments, 1 apart: merged they last 5 samples and must survive.
    score = [0, 5, 0, 5, 0, 5, 0]
    assert events(score, threshold=1, min_samples=3, merge_gap=1) == [(1, 6)]
    # Without merging the same fragments are all too short.
    assert events(score, threshold=1, min_samples=3, merge_gap=0) == []


# ---- contracts -----------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [dict(min_samples=0), dict(min_samples=-2), dict(merge_gap=-1)])
def test_invalid_parameters_raise(kwargs):
    with pytest.raises(ValueError):
        detect_events([0, 5, 0], threshold=1, **kwargs)


def test_two_dimensional_input_raises():
    with pytest.raises(ValueError):
        detect_events(np.zeros((3, 2)), threshold=1)


def test_input_is_not_modified():
    score = np.array([0.0, 5.0, np.nan, 5.0])
    before = score.copy()
    detect_events(score, threshold=1, merge_gap=1)
    np.testing.assert_array_equal(score, before)


# ---- properties over many random inputs ----------------------------------------------

def test_structural_properties_on_random_scores():
    rng = np.random.default_rng(7)
    for _ in range(200):
        score = rng.normal(size=int(rng.integers(0, 60)))
        min_samples, merge_gap = int(rng.integers(1, 5)), int(rng.integers(0, 4))
        out = events(score, threshold=0.2, min_samples=min_samples, merge_gap=merge_gap)
        covered = np.zeros(len(score), dtype=bool)
        previous_stop = None
        for start, stop in out:
            assert 0 <= start < stop <= len(score)
            assert stop - start >= min_samples
            assert score[start] > 0.2 and score[stop - 1] > 0.2      # events begin and end above threshold
            if previous_stop is not None:
                assert start - previous_stop > merge_gap             # otherwise they should have been merged
            previous_stop = stop
            covered[start:stop] = True
        if min_samples == 1:
            assert covered[score > 0.2].all()                        # nothing above threshold is lost
