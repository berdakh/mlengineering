"""error_segments: each run of wrong rows gets the kind of failure it is."""
from __future__ import annotations

import numpy as np
import pytest

from synth import call, experiment, seq, stack


def kinds(segments):
    return [(r.kind, r.start_t, r.end_t) for r in segments.sort_values(["experiment_id", "start_t"]).itertuples()]


def test_perfect_detection_has_no_error_segments(ea):
    tidy = experiment(seq((0, 50), (1, 50), (0, 20)), seq((0, 50), (1, 50), (0, 20)))
    assert len(call(ea.error_segments, tidy)) == 0


def test_event_never_flagged_is_a_miss(ea):
    tidy = experiment(seq((0, 50), (1, 60), (0, 10)), seq((0, 120)))
    assert kinds(call(ea.error_segments, tidy)) == [("miss", 50, 109)]


def test_late_detection_is_late_not_a_miss(ea):
    tidy = experiment(seq((0, 50), (1, 100)), seq((0, 50), (0, 45), (1, 55)))
    segments = call(ea.error_segments, tidy, late_after=30)
    assert kinds(segments) == [("late", 50, 94)], (
        "the event WAS detected, 45 rows after onset; calling it a miss throws away the difference "
        "between 'never noticed' and 'noticed too slowly'")
    assert segments.iloc[0]["n_rows"] == 45


def test_short_onset_latency_is_a_boundary_error(ea):
    tidy = experiment(seq((0, 50), (1, 100)), seq((0, 50), (0, 8), (1, 92)))
    assert kinds(call(ea.error_segments, tidy, late_after=30)) == [("boundary", 50, 57)]
    assert kinds(call(ea.error_segments, tidy, late_after=5)) == [("late", 50, 57)]


def test_latency_equal_to_the_tolerance_is_not_late(ea):
    tidy = experiment(seq((0, 20), (1, 80)), seq((0, 20), (0, 30), (1, 50)))
    assert kinds(call(ea.error_segments, tidy, late_after=30)) == [("boundary", 20, 49)]


def test_dropouts_after_detection_are_fragments(ea):
    labels = seq((0, 20), (1, 60), (0, 20))
    flags = seq((0, 20), (1, 10), (0, 15), (1, 10), (0, 5), (1, 10), (0, 10), (0, 20))
    assert kinds(call(ea.error_segments, experiment(labels, flags))) == [
        ("fragment", 30, 44), ("fragment", 55, 59), ("fragment", 70, 79)]


def test_false_alarm_runs_are_placed_relative_to_the_event(ea):
    labels = seq((0, 100), (1, 50), (0, 100))
    flags = seq((0, 10), (1, 5), (0, 85), (1, 50), (0, 60), (1, 40))
    assert kinds(call(ea.error_segments, experiment(labels, flags))) == [
        ("pre_onset", 10, 14), ("post_event", 210, 249)]


def test_false_alarm_in_an_experiment_without_events(ea):
    tidy = experiment(seq((0, 60)), seq((0, 20), (1, 7), (0, 33)), "valve2/0")
    assert kinds(call(ea.error_segments, tidy)) == [("false_alarm", 20, 26)]


def test_short_alarm_touching_the_event_edge_is_a_boundary_error(ea):
    labels = seq((0, 100), (1, 50), (0, 100))
    early = seq((0, 96), (1, 4), (1, 50), (0, 100))                 # alarm starts 4 rows before the labelled onset
    lingering = seq((0, 100), (1, 50), (1, 6), (0, 94))             # alarm clears 6 rows after the labelled end
    assert kinds(call(ea.error_segments, experiment(labels, early))) == [("boundary", 96, 99)]
    assert kinds(call(ea.error_segments, experiment(labels, lingering))) == [("boundary", 150, 155)]
    long_early = seq((0, 40), (1, 60), (1, 50), (0, 100))           # 60 rows early is not a labelling quibble
    assert kinds(call(ea.error_segments, experiment(labels, long_early), late_after=30)) == [("pre_onset", 40, 99)]


def test_segments_do_not_cross_experiments(ea):
    a = experiment(seq((0, 10), (1, 10)), seq((0, 10), (1, 5), (0, 5)), "valve1/0")       # ends with missed rows
    b = experiment(seq((1, 10), (0, 10)), seq((0, 4), (1, 6), (0, 10)), "valve1/1")       # starts with missed rows
    segments = call(ea.error_segments, stack(a, b))
    assert kinds(segments) == [("fragment", 15, 19), ("boundary", 0, 3)]
    assert segments["experiment_id"].tolist() == ["valve1/0", "valve1/1"]
    assert set(segments["family"]) == {"valve1"}


def test_burn_in_rows_are_ignored(ea):
    tidy = experiment(seq((0, 50), (1, 50)), seq((1, 6), (0, 44), (1, 50)))
    assert kinds(call(ea.error_segments, tidy)) == [("pre_onset", 0, 5)]
    assert len(call(ea.error_segments, tidy, burn_in=10)) == 0


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_segments_account_for_every_wrong_row_exactly_once(ea, seed):
    rng = np.random.default_rng(seed)
    frames = []
    for i in range(5):
        n = int(rng.integers(80, 200))
        labels = np.zeros(n, dtype=int)
        if i != 4:
            start = int(rng.integers(10, n - 40))
            labels[start:start + int(rng.integers(15, 30))] = 1
        flags = np.where(rng.random(n) < 0.25, 1 - labels, labels)
        frames.append(experiment(labels, flags, f"other/{i}"))
    tidy = stack(*frames)
    segments = call(ea.error_segments, tidy)
    wrong = int((tidy["anomaly"].to_numpy() != tidy["score"].to_numpy().astype(int)).sum())
    assert int(segments["n_rows"].sum()) == wrong
    assert (segments["end_t"] - segments["start_t"] + 1 == segments["n_rows"]).all()
    assert set(segments["kind"]) <= {"miss", "late", "boundary", "fragment", "pre_onset", "post_event", "false_alarm"}
    table = call(ea.per_experiment_table, tidy)
    assert wrong == int(table["fp"].sum() + table["fn"].sum())
