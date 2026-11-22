"""Reference hand-constructed cases for flowguard.evaluation (the lab's own tests, not the checks)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flowguard import evaluation as ev  # noqa: E402


def test_one_event_in_the_middle():
    assert ev.extract_events([0, 1, 1, 1, 0]) == [(1, 4)]


def test_events_touching_both_ends():
    assert ev.extract_events([1, 0, 0, 1, 1]) == [(0, 1), (3, 5)]


def test_chatter_is_merged_then_filtered():
    assert ev.extract_events([1, 0, 1, 0, 1, 0, 0, 0, 1], min_duration=3, merge_gap=1) == [(0, 5)]


def test_alarm_two_rows_after_onset():
    true, alarms = [(10, 20)], [(12, 15)]
    assert ev.event_recall(true, alarms) == 1.0
    assert list(ev.detection_delay(true, alarms)) == [2.0]


def test_two_alarms_in_one_event_are_one_hit():
    m = ev.match_events([(10, 30)], [(12, 14), (20, 22)])
    assert m["pred_label"] == ["hit", "redundant"]
    assert ev.event_precision([(10, 30)], [(12, 14), (20, 22)]) == 1.0


def test_alarm_already_on_is_a_false_alarm():
    m = ev.match_events([(10, 30)], [(5, 40)])
    assert m["pred_label"] == ["false_alarm"] and m["first_detection"] == [None]
    assert math.isinf(ev.detection_delay([(10, 30)], [(5, 40)])[0])


def test_two_second_sampling_and_a_gap():
    times = np.arange(50) * 2.0
    times[20:] += 100.0
    assert ev.detection_delay([(15, 30)], [(22, 25)], times=times)[0] == pytest.approx(114.0)
    assert ev.normal_hours([(15, 30)], times) == pytest.approx((14 + 20) * 2 / 3600)
    assert ev.false_alarms_per_hour([(15, 30)], [(2, 3), (40, 41)], times) == pytest.approx(2 / ((14 + 20) * 2 / 3600))


def test_missed_event_keeps_its_place():
    d = ev.detection_delay([(10, 20), (40, 50)], [(41, 42)])
    assert math.isinf(d[0]) and d[1] == 1.0
    assert math.isinf(ev.delay_summary(d)["median"])
