"""Challenge checks: time-based causal windows on irregular data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import FEATURES, WINDOWS, same, slow_reference


def test_row_alignment_and_columns(frame, compute):
    out = compute(frame)
    assert list(out.index) == list(frame.index)
    assert out["series_id"].tolist() == frame["series_id"].tolist()
    for column in [*FEATURES, "dt_prev_s", "segment"]:
        assert column in out.columns, f"missing column {column}"


def test_matches_slow_reference(frame, compute):
    out, ref = compute(frame), slow_reference(frame)
    for column in FEATURES:
        np.testing.assert_allclose(out[column].to_numpy(dtype=float), ref[column].to_numpy(),
                                   rtol=1e-8, atol=1e-8, equal_nan=True, err_msg=column)


@pytest.mark.parametrize("cut", [40, 75, 110])
def test_changing_the_future_changes_nothing_earlier(frame, compute, cut):
    before = compute(frame)
    series = frame["series_id"] == "freezer-A"
    cut_time = frame.loc[series, "timestamp"].sort_values().iloc[cut]
    later = series & (frame["timestamp"] > cut_time)
    perturbed = frame.copy()
    perturbed.loc[later, "value"] += 500.0
    after = compute(perturbed)
    earlier = (series & (frame["timestamp"] <= cut_time)).to_numpy()
    assert same(before.loc[earlier, FEATURES], after.loc[earlier, FEATURES]), "a feature read observations from its future"
    assert not same(before.loc[later.to_numpy(), FEATURES], after.loc[later.to_numpy(), FEATURES])


@pytest.mark.parametrize("cut", [40, 110])
def test_deleting_the_future_changes_nothing_earlier(frame, compute, cut):
    """Online, later rows have not arrived yet. Truncating the series must reproduce the same features."""
    full = compute(frame)
    series = frame["series_id"] == "freezer-B"
    cut_time = frame.loc[series, "timestamp"].sort_values().iloc[cut]
    truncated = frame[~(series & (frame["timestamp"] > cut_time))]
    short = compute(truncated)
    assert same(full.loc[truncated.index, FEATURES], short.loc[truncated.index, FEATURES])


def test_series_are_independent(frame, compute):
    before = compute(frame)
    altered = frame.copy()
    victim = altered["series_id"] == "freezer-C"
    altered.loc[victim, "value"] = 99.0
    after = compute(altered)
    assert same(before.loc[(~victim).to_numpy(), FEATURES], after.loc[(~victim).to_numpy(), FEATURES])


def test_row_order_of_the_input_does_not_matter(frame, compute):
    shuffled = frame.sample(frac=1.0, random_state=5)
    out = compute(shuffled)
    assert list(out.index) == list(shuffled.index), "output must keep the input's index and order"
    assert same(out.sort_index()[FEATURES], compute(frame)[FEATURES])


def test_windows_are_measured_in_seconds_not_rows(compute):
    """Same values, sampling twice as sparse: a 30 s window must then hold about half as many rows."""
    t0 = pd.Timestamp("2024-05-01")
    dense = pd.DataFrame({"series_id": "s", "timestamp": t0 + pd.to_timedelta(np.arange(200) * 2.0, unit="s"),
                          "value": np.arange(200.0)})
    sparse = dense.iloc[::2].reset_index(drop=True)
    assert compute(dense)["count_30s"].iloc[-1] == 15
    assert compute(sparse)["count_30s"].iloc[-1] == 8
    assert compute(dense)["mean_30s"].iloc[-1] == pytest.approx(np.arange(185.0, 200.0).mean())


def test_window_is_open_on_the_left_and_closed_on_the_right(compute):
    t0 = pd.Timestamp("2024-05-01")
    df = pd.DataFrame({"series_id": "s", "timestamp": t0 + pd.to_timedelta([0, 10, 20, 30, 40], unit="s"),
                       "value": [1.0, 2.0, 3.0, 4.0, 5.0]})
    out = compute(df, windows_s=(30.0,), max_gap_s=20.0)
    assert out["count_30s"].tolist() == [1, 2, 3, 3, 3], "the observation exactly w seconds old is outside (tau - w, tau]"
    assert np.isnan(out["mean_30s"].iloc[2]) and out["mean_30s"].iloc[3] == pytest.approx(3.0)
    assert out["mean_30s"].iloc[4] == pytest.approx(4.0)


def test_outage_resets_the_window(frame, compute):
    out = compute(frame)
    b = out[out["series_id"] == "freezer-B"].sort_values("timestamp")
    resume = b.iloc[71]
    assert resume["dt_prev_s"] == pytest.approx(300.0)
    assert resume["count_120s"] == 1 and np.isnan(resume["mean_120s"]) and np.isnan(resume["mean_30s"])
    assert b.iloc[70]["segment"] != resume["segment"]
    assert np.isnan(b.iloc[0]["dt_prev_s"])


def test_missing_column_is_a_value_error(frame, compute):
    with pytest.raises(ValueError):
        compute(frame.drop(columns=["timestamp"]))
