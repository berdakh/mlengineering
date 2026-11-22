"""Delay, censoring, hours of normal operation and false alarms per hour: time comes from timestamps."""
import math

import numpy as np
import pandas as pd
import pytest

import synth


def test_delay_in_rows_without_times(ev):
    d = ev.detection_delay([(10, 20), (40, 50)], [(13, 14), (40, 41)])
    assert list(np.asarray(d, dtype=float)) == [3.0, 0.0]


def test_delay_uses_the_sampling_interval(ev):
    times = np.arange(100) * 2.0                                  # one row every 2 s
    d = ev.detection_delay([(10, 20)], [(13, 14)], times=times)
    assert float(np.asarray(d)[0]) == pytest.approx(6.0)


def test_delay_accepts_datetimes(ev):
    stamps = pd.Timestamp("2024-03-01 10:00:00") + pd.to_timedelta(np.arange(100) * 5, unit="s")
    for times in (stamps, pd.Series(stamps), stamps.to_numpy()):
        d = ev.detection_delay([(10, 20)], [(14, 15)], times=times)
        assert float(np.asarray(d)[0]) == pytest.approx(20.0)


def test_delay_counts_wall_clock_time_across_a_gap(ev):
    times = np.arange(60, dtype=float)
    times[15:] += 300.0                                           # the logger dropped 5 minutes
    d = ev.detection_delay([(10, 30)], [(18, 20)], times=times)
    assert float(np.asarray(d)[0]) == pytest.approx(308.0)


def test_delay_is_never_negative_inside_the_early_tolerance(ev):
    d = ev.detection_delay([(10, 20)], [(8, 9)], early_tolerance=2)
    assert float(np.asarray(d)[0]) == 0.0


def test_missed_events_stay_in_the_result_as_infinite_delay(ev):
    d = np.asarray(ev.detection_delay([(10, 20), (40, 50), (70, 80)], [(15, 16)]), dtype=float)
    assert d.shape == (3,), "one delay per TRUE event, including the missed ones"
    assert d[0] == 5.0 and np.isinf(d[1]) and np.isinf(d[2])


def test_alarm_before_onset_does_not_produce_a_delay(ev):
    d = np.asarray(ev.detection_delay([(10, 20)], [(5, 15)]), dtype=float)
    assert np.isinf(d[0]), "an alarm that was already on is not a detection (and not a negative delay)"


def test_delay_summary_is_honest_about_missed_events(ev):
    s = ev.delay_summary([5.0, math.inf])
    assert s["n_events"] == 2 and s["n_detected"] == 1
    assert math.isinf(s["median"]), "with half of the events missed the median delay is not 5 s"
    s = ev.delay_summary([1.0, 2.0, math.inf])
    assert s["median"] == 2.0 and math.isinf(s["p90"])
    s = ev.delay_summary([3.0, 1.0, 2.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    assert 5.0 <= s["median"] <= 6.0 and 9.0 <= s["p90"] <= 10.0


def test_normal_hours_at_one_hertz(ev):
    assert ev.normal_hours([], np.arange(3601, dtype=float)) == pytest.approx(1.0)


def test_normal_hours_follow_the_clock_not_the_row_count(ev):
    assert ev.normal_hours([], np.arange(1801) * 2.0) == pytest.approx(1.0)       # 2 s sampling
    assert ev.normal_hours([], np.arange(361) * 10.0) == pytest.approx(1.0)       # 10 s sampling


def test_normal_hours_exclude_event_rows(ev):
    times = np.arange(7201, dtype=float)                                          # 2 h at 1 Hz
    assert ev.normal_hours([(1800, 3600)], times) == pytest.approx(1.5)


def test_normal_hours_with_a_gap_and_with_max_gap(ev):
    times = np.arange(1801, dtype=float)
    times[900:] += 1800.0                                                         # half an hour missing
    assert ev.normal_hours([], times) == pytest.approx(1.0)                       # wall clock
    assert ev.normal_hours([], times, max_gap=10.0) == pytest.approx((1799 + 10) / 3600)


def test_normal_hours_accept_datetimes(ev):
    stamps = pd.Timestamp("2024-03-01") + pd.to_timedelta(np.arange(721) * 5, unit="s")
    assert ev.normal_hours([], stamps.to_numpy()) == pytest.approx(1.0)


def test_false_alarms_per_hour(ev):
    times = np.arange(7201, dtype=float)                                          # 2 h, 1 h of it normal
    true = [(1800, 5400)]
    alarms = [(100, 105), (900, 901), (2000, 2100), (3000, 3001), (6000, 6050)]   # 3 false, 1 hit, 1 redundant
    assert ev.false_alarms_per_hour(true, alarms, times) == pytest.approx(3.0)
    assert ev.false_alarms_per_hour(true, alarms, times * 2.0) == pytest.approx(1.5)


def test_false_alarms_per_hour_is_nan_without_normal_time(ev):
    assert math.isnan(ev.false_alarms_per_hour([(0, 10)], [], np.arange(10, dtype=float)))


def test_pooled_evaluation_over_experiments(ev):
    """SYNTHETIC: two experiments, 2 s sampling, one logging gap, 10 burn-in rows each."""
    n = 210
    sec_a = np.arange(n) * 2.0
    sec_b = np.arange(n) * 2.0
    sec_b[150:] += 600.0                                                          # gap after the event
    y_a = np.zeros(n, dtype=int); y_a[60:110] = 1
    y_b = np.zeros(n, dtype=int); y_b[80:120] = 1
    tidy = pd.concat([synth.experiment("valve1/0", sec_a.tolist(), y_a.tolist()),
                      synth.experiment("other/1", sec_b.tolist(), y_b.tolist())], ignore_index=True)
    flag_a = np.zeros(n, dtype=int); flag_a[3:6] = 1; flag_a[30:32] = 1; flag_a[65:70] = 1; flag_a[90:95] = 1
    flag_b = np.zeros(n, dtype=int); flag_b[70:90] = 1; flag_b[180:181] = 1
    out = ev.evaluate_experiments(tidy, np.r_[flag_a, flag_b], burn_in=10)
    assert out["n_events"] == 2 and out["n_detected"] == 1          # B's alarm was already on at onset
    assert out["n_hits"] == 1 and out["n_redundant"] == 1
    assert out["n_false_alarms"] == 3                               # A: rows 30-31; B: rows 70-89 and row 180
    # normal time: A (199 intervals - 50 event rows) * 2 s; B (199 - 40) * 2 s + 600 s gap
    assert out["normal_hours"] == pytest.approx(((199 - 50) * 2 + (199 - 40) * 2 + 600) / 3600)
    assert out["false_alarms_per_hour"] == pytest.approx(3 / out["normal_hours"])
    assert sorted(out["delays_s"]) == [10.0, math.inf]
    assert math.isinf(out["median_delay_s"])


def test_delay_includes_the_rows_needed_to_confirm_an_alarm(ev):
    times = np.arange(100) * 2.0
    true, alarms = [(10, 60)], [(13, 40)]
    assert float(np.asarray(ev.detection_delay(true, alarms, times=times))[0]) == pytest.approx(6.0)
    confirmed = ev.detection_delay(true, alarms, times=times, confirm_rows=9)      # min_duration = 10
    assert float(np.asarray(confirmed)[0]) == pytest.approx(24.0)
    assert float(np.asarray(ev.detection_delay(true, alarms, confirm_rows=9))[0]) == 12.0   # in rows


def test_pooled_delay_reflects_min_duration(ev):
    """SYNTHETIC: one clean detection 4 rows after onset; a 20-row persistence requirement must cost 19 more."""
    n = 300
    y = np.zeros(n, dtype=int); y[100:200] = 1
    flags = np.zeros(n, dtype=int); flags[104:200] = 1
    tidy = synth.experiment("valve1/0", np.arange(n, dtype=float).tolist(), y.tolist())
    assert ev.evaluate_experiments(tidy, flags)["delays_s"] == [4.0]
    assert ev.evaluate_experiments(tidy, flags, min_duration=20)["delays_s"] == [23.0]
