"""Your own hand-constructed cases for flowguard.evaluation. Two are given; add yours BEFORE coding.

    python -m pytest labs/w3d4_point_vs_event_evaluation/lab/tests -q

Draw each case on paper first (a row of 0/1 for the truth, a row for the alarms) and write the
answer you expect under the conventions in the module docstring. Cases worth having: an event that
touches the first or last row, two alarms inside one event, an alarm that begins before the event,
a missed event, a recording sampled every 2 s, a logging gap.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flowguard import evaluation as ev  # noqa: E402


def test_one_event_in_the_middle():
    assert ev.extract_events([0, 1, 1, 1, 0]) == [(1, 4)]          # end is exclusive


def test_alarm_two_rows_after_onset():
    true, alarms = [(10, 20)], [(12, 15)]
    assert ev.event_recall(true, alarms) == 1.0
    assert list(ev.detection_delay(true, alarms)) == [2.0]
