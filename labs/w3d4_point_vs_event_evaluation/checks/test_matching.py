"""match_events / event_recall / event_precision under the start-based rule in the lab docstring."""
import math

import pytest


def detected(m):
    return [d is not None for d in m["first_detection"]]


def test_nothing_at_all(ev):
    m = ev.match_events([], [])
    assert list(m["first_detection"]) == [] and list(m["pred_label"]) == []
    assert math.isnan(ev.event_recall([], []))
    assert math.isnan(ev.event_precision([], []))


def test_alarms_without_any_true_event_are_all_false_alarms(ev):
    m = ev.match_events([], [(3, 5), (10, 11)])
    assert list(m["pred_label"]) == ["false_alarm", "false_alarm"]
    assert ev.event_precision([], [(3, 5), (10, 11)]) == 0.0


def test_true_events_without_alarms_are_all_missed(ev):
    m = ev.match_events([(10, 20), (30, 40)], [])
    assert detected(m) == [False, False]
    assert ev.event_recall([(10, 20), (30, 40)], []) == 0.0
    assert math.isnan(ev.event_precision([(10, 20), (30, 40)], []))


def test_fragmented_detection_is_one_hit_not_three(ev):
    true, alarms = [(10, 50)], [(12, 15), (20, 25), (30, 31)]
    m = ev.match_events(true, alarms)
    assert list(m["pred_label"]) == ["hit", "redundant", "redundant"]
    assert list(m["first_detection"]) == [12]
    assert ev.event_recall(true, alarms) == 1.0
    assert ev.event_precision(true, alarms) == 1.0


def test_redundant_alarms_do_not_dilute_precision(ev):
    true = [(10, 50)]
    alarms = [(2, 3), (12, 15), (20, 25), (30, 31), (40, 41)]      # 1 false alarm, 1 hit, 3 repeats
    assert ev.event_precision(true, alarms) == pytest.approx(0.5)


def test_alarm_already_on_before_onset_is_a_false_alarm_and_detects_nothing(ev):
    true, alarms = [(10, 20)], [(5, 15)]
    m = ev.match_events(true, alarms)
    assert list(m["pred_label"]) == ["false_alarm"]
    assert detected(m) == [False]
    assert ev.event_recall(true, alarms) == 0.0


def test_event_can_still_be_detected_by_a_later_alarm(ev):
    true, alarms = [(10, 20)], [(5, 12), (15, 18)]
    m = ev.match_events(true, alarms)
    assert list(m["pred_label"]) == ["false_alarm", "hit"]
    assert list(m["first_detection"]) == [15]


def test_early_tolerance_window(ev):
    true = [(10, 20)]
    assert list(ev.match_events(true, [(8, 9)], early_tolerance=2)["pred_label"]) == ["hit"]
    assert list(ev.match_events(true, [(8, 9)], early_tolerance=1)["pred_label"]) == ["false_alarm"]
    assert list(ev.match_events(true, [(8, 9)])["pred_label"]) == ["false_alarm"]


def test_event_end_is_exclusive(ev):
    true = [(10, 20)]
    assert list(ev.match_events(true, [(19, 25)])["pred_label"]) == ["hit"]
    assert list(ev.match_events(true, [(20, 25)])["pred_label"]) == ["false_alarm"]


def test_one_long_alarm_detects_only_the_event_it_started_in(ev):
    true, alarms = [(10, 20), (30, 40)], [(12, 45)]
    m = ev.match_events(true, alarms)
    assert detected(m) == [True, False]
    assert ev.event_recall(true, alarms) == 0.5


def test_mixed_case(ev):
    true = [(10, 20), (40, 50)]
    alarms = [(2, 4), (11, 13), (15, 30), (45, 60), (47, 48), (70, 71)]
    m = ev.match_events(true, alarms)
    assert list(m["pred_label"]) == ["false_alarm", "hit", "redundant", "hit", "redundant", "false_alarm"]
    assert list(m["first_detection"]) == [11, 45]
    assert ev.event_precision(true, alarms) == pytest.approx(0.5)


@pytest.mark.parametrize("shift", [1, 17, 1000])
def test_shifting_everything_in_time_changes_nothing_but_the_indices(ev, shift):
    true = [(10, 20), (40, 50)]
    alarms = [(2, 4), (11, 13), (15, 30), (45, 60), (70, 71)]
    base = ev.match_events(true, alarms, early_tolerance=1)
    moved = ev.match_events([(s + shift, e + shift) for s, e in true],
                            [(s + shift, e + shift) for s, e in alarms], early_tolerance=1)
    assert list(moved["pred_label"]) == list(base["pred_label"])
    assert list(moved["first_detection"]) == [d + shift for d in base["first_detection"]]
