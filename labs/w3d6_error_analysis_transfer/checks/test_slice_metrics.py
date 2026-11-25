"""slice_metrics: the experiment is the unit, sizes are reported, undefined stays undefined."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from synth import call, experiment, seq, stack


def by_slice(result: pd.DataFrame, name):
    hit = result[result["slice"] == name]
    assert len(hit) == 1, f"expected one row for slice {name!r}, got {len(hit)}"
    return hit.iloc[0]


def planted(ea) -> pd.DataFrame:
    """Family 'other': one long experiment detected perfectly and three short ones missed entirely.
    Row-pooled recall of 'other' is 600/690 = 0.87; three of its four experiments fail completely."""
    frames = [experiment(seq((0, 100), (1, 600)), seq((0, 100), (1, 600)), "other/0")]
    frames += [experiment(seq((0, 100), (1, 30)), seq((0, 130)), f"other/{i}") for i in (1, 2, 3)]
    frames += [experiment(seq((0, 100), (1, 100)), seq((0, 130), (1, 70)), f"valve1/{i}") for i in range(4)]
    frames += [experiment(seq((0, 100), (1, 100)), seq((0, 120), (1, 80)), f"valve2/{i}") for i in range(2)]
    return call(ea.per_experiment_table, stack(*frames))


def test_value_is_the_mean_over_experiments(ea):
    result = ea.slice_metrics(planted(ea), "family", "recall")
    assert by_slice(result, "other")["value"] == pytest.approx(0.25)
    assert by_slice(result, "valve1")["value"] == pytest.approx(0.70)
    assert by_slice(result, "valve2")["value"] == pytest.approx(0.80)


def test_the_planted_failing_slice_is_the_worst(ea):
    result = ea.slice_metrics(planted(ea), "family", "recall")
    worst = result.sort_values("value").iloc[0]
    assert worst["slice"] == "other", (
        "three of four 'other' experiments are missed completely; a row-pooled recall hides them "
        "behind one long experiment")


def test_slice_sizes_are_reported(ea):
    result = ea.slice_metrics(planted(ea), "family", "recall")
    other = by_slice(result, "other")
    assert other["n_experiments"] == 4 and other["n_defined"] == 4
    assert other["n_rows"] == 700 + 3 * 130
    assert by_slice(result, "valve2")["n_experiments"] == 2
    assert other["min"] == pytest.approx(0.0) and other["max"] == pytest.approx(1.0)


def test_requested_level_with_no_experiments_is_reported_as_empty(ea):
    result = ea.slice_metrics(planted(ea), "family", "recall", levels=["valve1", "valve2", "other", "pump"])
    pump = by_slice(result, "pump")
    assert pump["n_experiments"] == 0 and pump["n_defined"] == 0
    assert math.isnan(pump["value"]), "an empty slice has no measured value; 0.0 would read as total failure"


def test_slice_where_the_metric_is_undefined_everywhere(ea):
    frames = [experiment(seq((0, 50)), seq((0, 45), (1, 5)), f"valve2/{i}") for i in range(3)]   # no anomaly at all
    frames += [experiment(seq((0, 25), (1, 25)), seq((0, 30), (1, 20)), f"valve1/{i}") for i in range(3)]
    table = call(ea.per_experiment_table, stack(*frames))
    result = ea.slice_metrics(table, "family", "recall")
    valve2 = by_slice(result, "valve2")
    assert valve2["n_experiments"] == 3 and valve2["n_defined"] == 0
    assert math.isnan(valve2["value"])
    assert by_slice(result, "valve1")["value"] == pytest.approx(0.8)


def test_undefined_experiments_are_skipped_but_counted(ea):
    df = pd.DataFrame({"experiment_id": list("abcd"), "group": ["x"] * 4, "n_rows": [10] * 4,
                       "m": [0.2, np.nan, 0.6, np.nan]})
    x = by_slice(ea.slice_metrics(df, "group", "m"), "x")
    assert x["n_experiments"] == 4 and x["n_defined"] == 2
    assert x["value"] == pytest.approx(0.4)


def test_interval_only_with_enough_experiments(ea):
    df = pd.DataFrame({
        "experiment_id": [f"e{i}" for i in range(16)],
        "group": ["small"] * 4 + ["large"] * 12,
        "n_rows": [100] * 16,
        "m": [0.1, 0.9, 0.2, 0.8] + [0.3, 0.5, 0.7, 0.4, 0.6, 0.5, 0.2, 0.8, 0.5, 0.45, 0.55, 0.5],
    })
    result = ea.slice_metrics(df, "group", "m")
    small, large = by_slice(result, "small"), by_slice(result, "large")
    assert math.isnan(small["ci_low"]) and math.isnan(small["ci_high"]), (
        "four experiments do not support a bootstrap interval; report min and max instead")
    assert large["ci_low"] < large["value"] < large["ci_high"]
    assert 0.3 < large["ci_low"] and large["ci_high"] < 0.7
    again = by_slice(ea.slice_metrics(df, "group", "m"), "large")
    assert again["ci_low"] == large["ci_low"] and again["ci_high"] == large["ci_high"], "same seed, same interval"


def test_interval_collapses_when_experiments_agree(ea):
    df = pd.DataFrame({"experiment_id": [f"e{i}" for i in range(8)], "group": ["g"] * 8,
                       "n_rows": [5] * 8, "m": [0.75] * 8})
    g = by_slice(ea.slice_metrics(df, "group", "m"), "g")
    assert g["ci_low"] == pytest.approx(0.75) and g["ci_high"] == pytest.approx(0.75)


def test_unknown_column_is_an_error(ea):
    with pytest.raises(KeyError):
        ea.slice_metrics(planted(ea), "no_such_column", "recall")
