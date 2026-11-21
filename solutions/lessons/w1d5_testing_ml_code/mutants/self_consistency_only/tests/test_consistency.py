import numpy as np
import pytest

from pumpwatch.features import HIGH_BAND_HZ, LOW_BAND_HZ, band_power, build_feature_table, fill_gaps, line_length, peak_to_peak, rms, window_features
from pumpwatch.split import group_train_test_split


def test_features_are_reproducible(rng):
    x = rng.standard_normal(128)
    assert rms(x) == rms(x.copy())
    assert line_length(x) == line_length(x.copy())
    assert band_power(x, 256.0, 10, 40) == band_power(x.copy(), 256.0, 10, 40)


def test_window_features_agree_with_individual_functions(rng):
    x = rng.standard_normal(128)
    feats = window_features(x, 256.0)
    assert feats["rms"] == pytest.approx(rms(fill_gaps(x)))
    assert feats["line_length"] == pytest.approx(line_length(x))
    assert feats["p2p"] == pytest.approx(peak_to_peak(x))
    assert feats["bp_low"] == pytest.approx(band_power(x, 256.0, *LOW_BAND_HZ))
    assert feats["bp_high"] == pytest.approx(band_power(x, 256.0, *HIGH_BAND_HZ))
    assert feats["ratio"] == pytest.approx(window_features(x.copy(), 256.0)["ratio"])


def test_feature_table_matches_window_features(make_frame):
    df = make_frame(n_units=2, n_windows=2)
    table = build_feature_table(df, 256.0)
    first = df[(df.unit_id == "U00") & (df.window_id == 0)]
    assert table.iloc[0]["rms"] == pytest.approx(window_features(first["vibration"].to_numpy(), 256.0)["rms"])


def test_split_same_twice(make_frame):
    table = build_feature_table(make_frame(), 256.0)
    a, b = group_train_test_split(table, seed=1), group_train_test_split(table, seed=1)
    assert (a[0] == b[0]).all() and (a[1] == b[1]).all()
