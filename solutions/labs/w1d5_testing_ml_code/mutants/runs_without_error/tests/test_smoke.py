import numpy as np
import pytest

from pumpwatch.features import band_power, build_feature_table, fill_gaps, line_length, peak_to_peak, rms, window_features
from pumpwatch.io import load_windows
from pumpwatch.model import train_and_evaluate
from pumpwatch.split import group_train_test_split


def test_scalar_features_return_positive_floats(rng):
    x = rng.standard_normal(128)
    for fn in (rms, line_length, peak_to_peak):
        value = fn(np.abs(x).cumsum())
        assert isinstance(value, float) and value > 0
    assert band_power(x, 256.0, 10, 40) > 0


def test_fill_gaps_removes_nans():
    assert not np.isnan(fill_gaps(np.array([1.0, np.nan, 3.0]))).any()


def test_window_features_finite(rng):
    assert all(np.isfinite(v) for v in window_features(rng.standard_normal(128), 256.0).values())


def test_pipeline_runs(make_frame, tmp_path):
    path = tmp_path / "w.csv"
    make_frame().to_csv(path, index=False)
    table = build_feature_table(load_windows(path), 256.0)
    train_idx, test_idx = group_train_test_split(table)
    assert len(train_idx) > 0 and len(test_idx) > 0
    assert 0.0 <= train_and_evaluate(table)["auc"] <= 1.0


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_windows(tmp_path / "nope.csv")
