"""Tasks 1-3: joining late labels, precision among labelled alarms, recall from distinct faults."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from conftest import alarms_table, day, reports_table, verdicts_table


def _verdict(joined, alarm_id):
    v = joined.set_index("alarm_id").loc[alarm_id, "verdict"]
    return None if pd.isna(v) else bool(v)


def test_join_keeps_one_row_per_alarm_in_input_order(de):
    alarms = alarms_table([("a2", 2, 5.0), ("a1", 1, 9.0), ("a3", 3, 7.0)])
    verdicts = verdicts_table([("a1", True, "f1", 6), ("a2", False, None, 4)])
    joined, report = de.join_verdicts(alarms, verdicts)
    assert list(joined["alarm_id"]) == ["a2", "a1", "a3"]
    assert _verdict(joined, "a1") is True and _verdict(joined, "a2") is False and _verdict(joined, "a3") is None
    assert report["n_alarms"] == 3 and report["n_labelled"] == 2 and report["n_pending"] == 1


def test_latest_label_time_wins_even_when_rows_arrive_out_of_order(de):
    alarms = alarms_table([("a1", 1, 9.0)])
    # the correction (True, day 9) is listed BEFORE the wrong first verdict (False, day 5)
    verdicts = verdicts_table([("a1", True, "f1", 9), ("a1", False, None, 5)])
    joined, report = de.join_verdicts(alarms, verdicts)
    assert _verdict(joined, "a1") is True
    assert joined.set_index("alarm_id").loc["a1", "fault_id"] == "f1"
    assert report["superseded"] == 1


def test_labels_after_as_of_do_not_exist_yet(de):
    alarms = alarms_table([("a1", 1, 9.0), ("a2", 2, 8.0)])
    verdicts = verdicts_table([("a1", False, None, 5), ("a1", True, "f1", 9), ("a2", True, "f2", 12)])
    joined, _ = de.join_verdicts(alarms, verdicts, as_of=day(7))
    assert _verdict(joined, "a1") is False          # the correction on day 9 is not known on day 7
    assert _verdict(joined, "a2") is None
    joined, _ = de.join_verdicts(alarms, verdicts, as_of=day(9))
    assert _verdict(joined, "a1") is True


def test_orphan_verdicts_are_counted_not_joined(de):
    alarms = alarms_table([("a1", 1, 9.0)])
    verdicts = verdicts_table([("a1", True, "f1", 3), ("zz", True, "f9", 3), ("yy", False, None, 4)])
    joined, report = de.join_verdicts(alarms, verdicts)
    assert len(joined) == 1 and report["orphan_verdicts"] == 2


def test_precision_excludes_pending_alarms(de):
    alarms = alarms_table([(f"a{i}", i, float(i)) for i in range(10)])
    verdicts = verdicts_table([(f"a{i}", i % 2 == 0, f"f{i}" if i % 2 == 0 else None, 20) for i in range(6)])
    joined, _ = de.join_verdicts(alarms, verdicts)
    p = de.alarm_precision(joined, min_labelled=5)
    assert p["status"] == "ok"
    assert p["k"] == 3 and p["n"] == 6 and p["n_pending"] == 4
    assert p["estimate"] == pytest.approx(0.5)
    assert p["low"] == pytest.approx(0.1876, abs=1e-3) and p["high"] == pytest.approx(0.8124, abs=1e-3)


def test_too_few_labels_is_insufficient_not_zero(de):
    alarms = alarms_table([("a1", 1, 9.0), ("a2", 2, 8.0)])
    verdicts = verdicts_table([("a1", False, None, 3)])
    joined, _ = de.join_verdicts(alarms, verdicts)
    p = de.alarm_precision(joined, min_labelled=5)
    assert p["status"] == "insufficient_data"
    assert math.isnan(p["estimate"]) and math.isnan(p["low"]) and math.isnan(p["high"])
    assert p["n"] == 1 and p["n_pending"] == 1


def test_verification_bias_known_answer(de):
    """20 alarms; the 10 with the highest peak scores are true. Operators investigate the top half:
    measured precision is 1.0 while the true precision is 0.5. The function must report what was
    measured (1.0 on 10 labelled) and the 10 pending alarms; it cannot know the truth."""
    alarms = alarms_table([(f"a{i}", i, float(i)) for i in range(20)])
    truth = {f"a{i}": i >= 10 for i in range(20)}
    investigated = [a for a in truth if int(a[1:]) >= 10]
    verdicts = verdicts_table([(a, truth[a], f"f{a}" if truth[a] else None, 30) for a in investigated])
    joined, _ = de.join_verdicts(alarms, verdicts)
    p = de.alarm_precision(joined, min_labelled=5)
    assert p["estimate"] == pytest.approx(1.0) and p["n"] == 10 and p["n_pending"] == 10
    true_precision = sum(truth.values()) / len(truth)
    assert p["estimate"] - true_precision == pytest.approx(0.5)


def test_recall_counts_distinct_faults_and_only_known_reports(de):
    alarms = alarms_table([("a1", 1, 9.0), ("a2", 1.1, 8.0), ("a3", 3, 7.0), ("a4", 4, 6.0), ("a5", 5, 5.0),
                           ("a6", 6, 5.0)])
    verdicts = verdicts_table([("a1", True, "f1", 4), ("a2", True, "f1", 4),   # two alarms, one fault
                               ("a3", True, "f3", 6), ("a4", True, "f4", 6), ("a5", True, "f5", 7),
                               ("a6", False, None, 8)])
    reports = reports_table([("f7", 2, 20), ("f8", 3, 40), ("f1", 1, 25)])     # f1 was caught: not a miss
    joined, _ = de.join_verdicts(alarms, verdicts)
    r = de.recall_estimate(joined, reports, as_of=day(30), min_events=5)
    assert r["n_caught"] == 4 and r["n_missed_reported"] == 1
    assert r["estimate"] == pytest.approx(4 / 5) and r["status"] == "ok"
    r = de.recall_estimate(joined, reports, as_of=day(50), min_events=5)
    assert r["n_missed_reported"] == 2 and r["estimate"] == pytest.approx(4 / 6)
    assert 0 <= r["low"] < r["estimate"] < r["high"] <= 1


def test_recall_with_no_events_is_insufficient(de):
    alarms = alarms_table([("a1", 1, 9.0)])
    joined, _ = de.join_verdicts(alarms, verdicts_table([("a1", False, None, 3)]))
    r = de.recall_estimate(joined, reports_table([]), min_events=1)
    assert r["status"] == "insufficient_data" and math.isnan(r["estimate"])
