import pytest

from eventkit.events import detect_events


def test_single_event():
    assert detect_events([0, 0, 5, 5, 5, 0, 0], threshold=1) == [(2, 5)]


def test_two_events():
    assert detect_events([0, 9, 9, 0, 0, 0, 9, 9, 9, 0], threshold=1) == [(1, 3), (6, 9)]


def test_short_event_removed():
    assert detect_events([0, 9, 0, 0, 0, 9, 9, 9, 9, 0], threshold=1, min_samples=3) == [(5, 9)]


def test_close_events_merged():
    assert detect_events([0, 9, 9, 0, 9, 9, 0], threshold=1, merge_gap=3) == [(1, 6)]


def test_no_events():
    assert detect_events([0, 0, 0], threshold=1) == []


def test_bad_min_samples():
    with pytest.raises(ValueError):
        detect_events([0, 9, 0], threshold=1, min_samples=0)
