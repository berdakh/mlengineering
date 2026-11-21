"""Behavioural contract: same numbers as the script, from any directory, leakage removed."""
import json
import shutil

import numpy as np
import pandas as pd
import pytest

# Printed by lab/messy_analysis.py on the committed synthetic data (seed 7, 30% of units held out).
GOLDEN = {"auc": 0.9992283950617284, "ap": 0.9970760233918129, "acc": 0.9666666666666667, "f1": 0.9090909090909091}
GOLDEN_TEST_UNITS = ["P01", "P06", "P09"]


@pytest.fixture(scope="module")
def features(pkg, data_csv):
    return pkg["features"].build_feature_table(pkg["io"].load_windows(data_csv), fs=256)


def test_cli_reproduces_the_script_from_another_directory(run_cli, data_csv, tmp_path):
    # The data is copied under a different name: a path baked into the code cannot find it.
    data = tmp_path / "elsewhere" / "plant_b.csv"
    data.parent.mkdir()
    shutil.copy(data_csv, data)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    proc = run_cli(["train", "--data", data], cwd=cwd)
    assert proc.returncode == 0, f"CLI failed outside the repo root:\n{proc.stderr[-800:]}"
    try:
        metrics = json.loads(proc.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"stdout must be exactly one JSON object, got:\n{proc.stdout[:300]}")
    for key, expected in GOLDEN.items():
        assert metrics[key] == pytest.approx(expected, abs=1e-6), f"{key} differs from the characterization run"
    assert sorted(metrics["test_units"]) == GOLDEN_TEST_UNITS


def test_cli_missing_file_is_a_clean_error(run_cli, tmp_path):
    proc = run_cli(["train", "--data", tmp_path / "nope.csv"], cwd=tmp_path)
    assert proc.returncode != 0, "a missing data file must give a non-zero exit code"
    assert "Traceback" not in proc.stderr, "report a one-line error on stderr, not a traceback"
    assert proc.stderr.strip(), "say what went wrong on stderr"


def test_load_windows_rejects_missing_columns(pkg, data_csv, tmp_path):
    bad = tmp_path / "bad.csv"
    pd.read_csv(data_csv, nrows=50).drop(columns=["label"]).to_csv(bad, index=False)
    with pytest.raises(ValueError):
        pkg["io"].load_windows(bad)


def test_feature_table_shape_and_values(features):
    assert len(features) == 300, "one row per (unit_id, window_id)"
    assert not features[["unit_id", "window_id"]].duplicated().any()
    for col in ("rms", "line_length", "p2p", "bp_low", "bp_high", "ratio", "temp", "label"):
        assert col in features.columns, f"missing column {col}"
    first = features[(features.unit_id == "P01") & (features.window_id == 0)].iloc[0]
    assert first["rms"] == pytest.approx(0.713007, abs=1e-5)
    assert first["bp_high"] == pytest.approx(0.063334, abs=1e-5)
    assert not features.drop(columns=["unit_id"]).isna().any().any(), "gaps must be filled before computing features"


def test_split_keeps_units_intact(pkg, features):
    train_idx, test_idx = pkg["split"].group_train_test_split(features, test_fraction=0.3, seed=7)
    train_units = set(features["unit_id"].iloc[train_idx])
    test_units = set(features["unit_id"].iloc[test_idx])
    assert train_units and test_units and not (train_units & test_units)
    assert len(train_idx) + len(test_idx) == len(features)


def test_train_and_evaluate_matches_golden(pkg, features):
    metrics = pkg["model"].train_and_evaluate(features, test_fraction=0.3, seed=7, C=1.0)
    for key, expected in GOLDEN.items():
        assert metrics[key] == pytest.approx(expected, abs=1e-6)


def test_scaling_lives_inside_the_model(pkg, features):
    """A model that owns its scaler gives the same probabilities when raw feature
    units change (volts -> millivolts). An L2-regularised logistic regression fed
    unscaled columns does not. This is the behavioural signature of 'the scaler is
    fitted wherever the model is fitted', i.e. on training rows only."""
    cols = [c for c in ("rms", "line_length", "p2p", "bp_low", "bp_high", "ratio", "temp") if c in features]
    X = features[cols].to_numpy(dtype=float)
    y = features["label"].to_numpy()
    units = np.array([1000.0, 0.01, 50.0, 1e4, 1e-3, 7.0, 0.5])[: X.shape[1]]
    p_raw = pkg["model"].make_model(C=1.0).fit(X[:200], y[:200]).predict_proba(X[200:])[:, 1]
    p_rescaled = pkg["model"].make_model(C=1.0).fit(X[:200] * units, y[:200]).predict_proba(X[200:] * units)[:, 1]
    assert np.allclose(p_raw, p_rescaled, atol=1e-4), (
        "make_model() must return ONE estimator that scales and classifies; "
        "scaling done outside it (before the split) is the leak from the original script"
    )
