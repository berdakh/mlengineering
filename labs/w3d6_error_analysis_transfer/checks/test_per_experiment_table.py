"""per_experiment_table: one honest row per experiment."""
from __future__ import annotations

import math

import numpy as np
import pytest

from synth import call, experiment, seq, stack


def row(table, experiment_id):
    hit = table[table["experiment_id"] == experiment_id]
    assert len(hit) == 1, f"expected exactly one row for {experiment_id}, got {len(hit)}"
    return hit.iloc[0]


def test_counts_and_rates_on_a_hand_built_experiment(ea):
    #        t: 0-9 normal (2 flagged), 10-19 anomalous (first flag at t=13, 6 flagged), 20-24 normal
    labels = seq((0, 10), (1, 10), (0, 5))
    flags = seq((0, 4), (1, 2), (0, 4), (0, 3), (1, 4), (0, 1), (1, 2), (0, 5))
    r = row(call(ea.per_experiment_table, experiment(labels, flags)), "valve1/0")
    assert (r["n_rows"], r["n_pos"], r["n_flagged"]) == (25, 10, 8)
    assert (r["tp"], r["fp"], r["fn"]) == (6, 2, 4)
    assert r["precision"] == pytest.approx(6 / 8)
    assert r["recall"] == pytest.approx(6 / 10)
    assert r["false_alarm_rate"] == pytest.approx(2 / 15)
    assert r["onset_t"] == 10 and r["first_detection_t"] == 13 and r["detection_delay"] == 3


def test_one_row_per_experiment_with_family(ea):
    tidy = stack(experiment(seq((0, 5), (1, 5)), seq((0, 5), (1, 5)), "valve1/0"),
                 experiment(seq((0, 5), (1, 5)), seq((0, 10)), "other/3"),
                 experiment(seq((0, 5), (1, 5)), seq((1, 10)), "valve2/1"))
    table = call(ea.per_experiment_table, tidy)
    assert sorted(table["experiment_id"]) == ["other/3", "valve1/0", "valve2/1"]
    assert row(table, "other/3")["family"] == "other"
    assert row(table, "valve1/0")["recall"] == pytest.approx(1.0)
    assert row(table, "other/3")["recall"] == pytest.approx(0.0)
    assert row(table, "valve2/1")["precision"] == pytest.approx(0.5)


def test_undefined_quantities_are_nan_not_zero(ea):
    nothing_flagged = experiment(seq((0, 5), (1, 5)), seq((0, 10)), "valve1/0")
    no_positives = experiment(seq((0, 10)), seq((0, 3), (1, 2), (0, 5)), "valve1/1")
    table = call(ea.per_experiment_table, stack(nothing_flagged, no_positives))
    a, b = row(table, "valve1/0"), row(table, "valve1/1")
    assert math.isnan(a["precision"]), "nothing was flagged: precision is undefined, not 0"
    assert a["recall"] == pytest.approx(0.0), "there were positives and none was found: recall IS 0"
    assert math.isnan(a["detection_delay"]) and math.isnan(a["first_detection_t"])
    assert math.isnan(b["recall"]), "no positives: recall is undefined, not 0"
    assert math.isnan(b["onset_t"]) and math.isnan(b["detection_delay"])
    assert b["false_alarm_rate"] == pytest.approx(0.2)


def test_a_flag_before_onset_is_not_a_detection(ea):
    labels = seq((0, 10), (1, 10))
    flags = seq((0, 2), (1, 3), (0, 5), (0, 6), (1, 4))
    r = row(call(ea.per_experiment_table, experiment(labels, flags)), "valve1/0")
    assert r["first_detection_t"] == 16 and r["detection_delay"] == 6


def test_threshold_is_inclusive(ea):
    tidy = experiment(seq((0, 2), (1, 2)), seq((0, 4)))
    scores = np.array([0.1, 0.5, 0.5, 0.49])
    r = row(ea.per_experiment_table(scores, tidy["anomaly"].to_numpy(), 0.5, tidy), "valve1/0")
    assert (r["tp"], r["fp"], r["fn"]) == (1, 1, 1)


def test_burn_in_rows_are_ignored(ea):
    labels = seq((0, 10), (1, 10))
    flags = seq((1, 4), (0, 6), (1, 10))          # four false alarms, all inside the burn-in
    tidy = experiment(labels, flags)
    assert row(call(ea.per_experiment_table, tidy), "valve1/0")["fp"] == 4
    r = row(call(ea.per_experiment_table, tidy, burn_in=5), "valve1/0")
    assert r["fp"] == 0 and r["n_rows"] == 15 and r["onset_t"] == 10


def test_row_order_of_the_input_does_not_matter(ea):
    tidy = stack(experiment(seq((0, 6), (1, 6)), seq((0, 8), (1, 4)), "valve1/0"),
                 experiment(seq((0, 4), (1, 8)), seq((0, 4), (1, 8)), "other/1"))
    shuffled = tidy.sample(frac=1.0, random_state=3).reset_index(drop=True)
    a = call(ea.per_experiment_table, tidy).set_index("experiment_id").sort_index()
    b = call(ea.per_experiment_table, shuffled).set_index("experiment_id").sort_index()
    for column in ("tp", "fp", "fn", "onset_t", "detection_delay"):
        assert a[column].tolist() == b[column].tolist(), column


def test_misaligned_inputs_are_rejected(ea):
    tidy = experiment(seq((0, 5), (1, 5)), seq((0, 10)))
    with pytest.raises(ValueError):
        ea.per_experiment_table(np.zeros(9), tidy["anomaly"].to_numpy(), 0.5, tidy)
