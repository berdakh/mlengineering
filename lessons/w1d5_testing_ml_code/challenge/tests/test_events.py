"""Your tests for eventkit.events.detect_events. Write them from the specification.

    cd lessons/w1d5_testing_ml_code/challenge
    python -m pytest -q
"""
from eventkit.events import detect_events


def test_single_event_in_the_middle():
    assert detect_events([0, 0, 5, 5, 5, 0, 0], threshold=1) == [(2, 5)]
