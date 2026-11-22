"""Tasks 4-5: windows by event time with labels known at as_of; keeping the two questions apart."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from conftest import alarms_table, day, reports_table, verdicts_table


def test_windows_use_event_time_and_as_of(de):
    alarms = alarms_table([("a1", 1, 9.0), ("a2", 2, 9.0), ("a3", 8, 9.0)])
    verdicts = verdicts_table([("a1", True, "f1", 3), ("a2", False, None, 9), ("a3", True, "f3", 9.5)])
    reports = reports_table([("f9", 2, 12)])
    wm = de.window_metrics(alarms, verdicts, reports, day(0), day(14), "7D", as_of=day(10),
                           min_labelled=1, min_events=1)
    assert len(wm) == 2
    assert list(pd.to_datetime(wm["window_start"])) == [day(0), day(7)]
    w0, w1 = wm.iloc[0], wm.iloc[1]
    # a2's verdict (day 9) counts in window 0 because the ALARM happened on day 2
    assert w0["n_alarms"] == 2 and w0["n_labelled"] == 2 and w0["precision"] == pytest.approx(0.5)
    assert w0["n_missed_reported"] == 0                      # report arrives on day 12 > as_of
    assert w1["n_alarms"] == 1 and w1["n_caught"] == 1
    wm = de.window_metrics(alarms, verdicts, reports, day(0), day(14), "7D", as_of=day(13),
                           min_labelled=1, min_events=1)
    assert wm.iloc[0]["n_missed_reported"] == 1 and wm.iloc[0]["recall"] == pytest.approx(0.5)


def test_window_without_labels_reports_insufficient_data(de):
    alarms = alarms_table([("a1", 1, 9.0), ("a2", 9, 9.0)])
    verdicts = verdicts_table([("a1", True, "f1", 3)])
    wm = de.window_metrics(alarms, verdicts, reports_table([]), day(0), day(14), "7D", as_of=day(20),
                           min_labelled=1, min_events=1)
    w1 = wm.iloc[1]
    assert w1["precision_status"] == "insufficient_data" and math.isnan(w1["precision"])
    assert w1["recall_status"] == "insufficient_data" and math.isnan(w1["recall"])
    assert w1["n_pending"] == 1


def _window(precision, recall, n_p, n_r, de):
    from flowguard.uncertainty import wilson_interval
    pl, ph = wilson_interval(round(precision * n_p), n_p) if n_p else (np.nan, np.nan)
    rl, rh = wilson_interval(round(recall * n_r), n_r) if n_r else (np.nan, np.nan)
    return pd.Series({"precision": precision if n_p else np.nan, "precision_low": pl, "precision_high": ph,
                      "precision_status": "ok" if n_p else "insufficient_data",
                      "recall": recall if n_r else np.nan, "recall_low": rl, "recall_high": rh,
                      "recall_status": "ok" if n_r else "insufficient_data"})


BASE = {"precision": 0.9, "recall": 0.8}


def test_drift_without_degradation(de):
    rep = de.monitor_report({"drift": True}, _window(0.9, 0.82, 100, 100, de), BASE, margin=0.1)
    assert rep["input_changed"] is True and rep["model_ok"] == "yes"
    assert "no model action" in rep["action"]


def test_degradation_without_drift(de):
    rep = de.monitor_report({"drift": False}, _window(0.9, 0.3, 100, 60, de), BASE, margin=0.1)
    assert rep["input_changed"] is False and rep["model_ok"] == "no"
    assert "escalate" in rep["action"]


def test_drift_does_not_decide_model_health(de):
    for drift in (True, False):
        rep = de.monitor_report({"drift": drift}, _window(0.9, 0.8, 0, 0, de), BASE)
        assert rep["model_ok"] == "unknown"
        rep = de.monitor_report({"drift": drift}, _window(0.9, 0.8, 200, 200, de), BASE)
        assert rep["model_ok"] == "yes"


def test_small_samples_are_inconclusive_not_verdicts(de):
    rep = de.monitor_report({"drift": False}, _window(0.9, 0.6, 10, 10, de), BASE, margin=0.1)
    assert rep["model_ok"] == "inconclusive"


def test_unmonitored_metric_is_ignored(de):
    rep = de.monitor_report({"drift": False}, _window(0.2, 0.85, 100, 100, de), {"precision": None, "recall": 0.8})
    assert rep["model_ok"] == "yes" and rep["precision_ok"] == "not_monitored"
