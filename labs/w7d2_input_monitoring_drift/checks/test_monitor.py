"""DriftMonitor: cadence, schema vs missingness vs drift, detection, and calibrated false alarms."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import SCALE, SENSORS, stable_run

WINDOW = 120


@pytest.fixture(scope="module")
def reference():
    return pd.concat([stable_run(600, seed) for seed in range(100, 106)], ignore_index=True)


@pytest.fixture(scope="module")
def thresholds(drift, reference):
    runs = [stable_run(1200, seed) for seed in range(200, 230)]
    return drift.calibrate_thresholds(reference, runs, SENSORS, WINDOW, "w1", 0.05)


def test_one_report_per_window_whatever_the_batch_size(drift, reference):
    mon = drift.DriftMonitor(reference, SENSORS, WINDOW)
    run = stable_run(600, 1)
    reports = []
    for start in range(0, len(run), 37):
        reports += mon.update(run.iloc[start:start + 37])
    assert len(reports) == 5, f"600 rows / window 120 -> 5 reports, got {len(reports)}"
    assert [r.window_index for r in reports] == list(range(5))
    assert all(r.n_rows == WINDOW for r in reports)
    assert mon.update(run.iloc[:50]) == [], "a partial window produces no report"


def test_schema_violations_are_counted_and_excluded(drift, reference, thresholds):
    run = stable_run(WINDOW, 2).copy()
    run.loc[3:9, "flow_rate"] = -9999.0          # 7 sentinel values
    run.loc[20:22, "current"] = np.inf           # 3 non-finite values
    rep = drift.DriftMonitor(reference, SENSORS, WINDOW, thresholds).update(run)[0]
    assert rep.n_schema_violations == 10
    assert rep.schema_alert
    assert not rep.drift_alert, f"violations must not reach the statistics; alerts {rep.alerts}"
    assert np.isfinite(rep.stats["flow_rate"]["w1"]) and rep.stats["flow_rate"]["w1"] < 1.0


def test_missing_values_are_missingness_not_violations(drift, reference, thresholds):
    run = stable_run(WINDOW, 3).copy()
    run.loc[::5, "pressure"] = np.nan            # 20 % missing
    rep = drift.DriftMonitor(reference, SENSORS, WINDOW, thresholds).update(run)[0]
    assert rep.n_schema_violations == 0
    assert rep.missing["pressure"] == pytest.approx(0.2)
    assert ("pressure", "missing") in {(s, k) for s, k, *_ in rep.alerts}
    assert not rep.drift_alert


def test_planted_shift_is_detected_quickly_and_attributed(drift, reference, thresholds):
    run = stable_run(1200, 4).copy()
    shift_at = 600                               # window 5 starts here
    run.loc[shift_at:, "thermocouple"] += 2.0 * SCALE["thermocouple"]     # a 2-SD level shift
    reports = drift.DriftMonitor(reference, SENSORS, WINDOW, thresholds).update(run)
    before = [r.window_index for r in reports if r.drift_alert and r.window_index < 5]
    after = [r for r in reports if r.drift_alert and r.window_index >= 5]
    assert len(before) <= 1, f"too many alerts before the shift: windows {before}"
    assert after and after[0].window_index <= 6, "a 2-SD shift starting in window 5 should alert by window 6"
    assert {s for s, k, *_ in after[0].alerts if k == "w1"} == {"thermocouple"}


def test_calibrated_thresholds_hold_the_false_alarm_rate_on_new_stable_data(drift, reference, thresholds):
    assert set(thresholds) == set(SENSORS) and all("w1" in v for v in thresholds.values())
    held_out = [stable_run(1200, seed) for seed in range(300, 340)]
    reports = []
    for run in held_out:
        reports += drift.DriftMonitor(reference, SENSORS, WINDOW, thresholds).update(run)
    rate = drift.alarm_rate(reports)
    assert rate <= 0.10, f"target 5 % of windows, measured {rate:.1%} on held-out stable data"


def test_calibration_depends_only_on_its_inputs(drift, reference):
    runs = [stable_run(600, seed) for seed in range(400, 405)]
    a = drift.calibrate_thresholds(reference, runs, SENSORS, WINDOW, "ks", 0.05)
    b = drift.calibrate_thresholds(reference, runs, SENSORS, WINDOW, "ks", 0.05)
    assert a == b
    with pytest.raises(ValueError):
        drift.calibrate_thresholds(reference, runs, SENSORS, WINDOW, "mean", 0.05)
