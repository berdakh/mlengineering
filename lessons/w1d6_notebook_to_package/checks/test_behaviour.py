"""Behaviour of flowguard.data and the `flowguard summary` command on SYNTHETIC SKAB-format files."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from conftest import CANONICAL_SENSORS, RAW_SENSORS, SPEC, TIDY_COLUMNS, make_raw_frame, write_raw


def test_sensor_columns_constant(data_module):
    assert list(data_module.SENSOR_COLUMNS) == CANONICAL_SENSORS


def test_load_experiment_columns_and_types(data_module, raw_dir):
    df = data_module.load_experiment(raw_dir / "valve1" / "0.csv")
    assert set(["datetime", *CANONICAL_SENSORS, "anomaly", "changepoint"]) <= set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["datetime"]), "datetime must be parsed, not left as text"
    assert pd.api.types.is_integer_dtype(df["anomaly"]) and pd.api.types.is_integer_dtype(df["changepoint"])
    assert len(df) == 20 and int(df["anomaly"].sum()) == 10 and int(df["changepoint"].sum()) == 1


def test_values_land_in_the_right_columns(data_module, raw_dir):
    df = data_module.load_experiment(raw_dir / "valve1" / "0.csv")
    for i, name in enumerate(CANONICAL_SENSORS):          # synthetic sensor i is centred on 10*(i+1)
        assert df[name].mean() == pytest.approx(10.0 * (i + 1), abs=2.0), name


def test_reordered_columns_are_not_silently_mislabelled(data_module, tmp_path):
    """Assigning names by position trusts the file's column order. Either map by name or refuse."""
    frame = make_raw_frame(15, "2020-01-01 00:00:00", True, seed=7)
    path = tmp_path / "valve1" / "0.csv"
    write_raw(path, frame[["datetime", *RAW_SENSORS[::-1], "changepoint", "anomaly"]])
    try:
        df = data_module.load_experiment(path)
    except ValueError:
        return                                            # refusing loudly is acceptable
    assert df["flow_rate"].tolist() == pytest.approx(frame["Volume Flow RateRMS"].tolist())
    assert df["accelerometer1_rms"].tolist() == pytest.approx(frame["Accelerometer1RMS"].tolist())
    assert int(df["anomaly"].sum()) == int(frame["anomaly"].sum())


def test_rows_sorted_by_time_even_if_file_is_not(data_module, raw_dir):
    df = data_module.load_experiment(raw_dir / "valve1" / "2.csv")
    assert df["datetime"].is_monotonic_increasing


def test_file_without_labels_is_kept_as_normal(data_module, raw_dir):
    df = data_module.load_experiment(raw_dir / "anomaly-free" / "anomaly-free.csv")
    assert len(df) == 40
    assert df["anomaly"].eq(0).all() and df["changepoint"].eq(0).all()
    assert not df[["anomaly", "changepoint"]].isna().any().any()


def test_missing_column_raises_and_names_it(data_module, tmp_path):
    path = tmp_path / "valve1" / "0.csv"
    write_raw(path, make_raw_frame(5, "2020-01-01 00:00:00", True, 0).drop(columns=["Pressure"]))
    with pytest.raises(ValueError, match="(?i)pressure"):
        data_module.load_experiment(path)


def test_missing_file_raises(data_module, tmp_path):
    with pytest.raises(FileNotFoundError):
        data_module.load_experiment(tmp_path / "absent.csv")


def test_experiment_ids_come_from_file_names(tidy):
    """`valve1/10.csv` is experiment `valve1/10`, whatever position it has in a sorted listing."""
    sizes = tidy.groupby("experiment_id").size().to_dict()
    assert sizes == {experiment_id: n for experiment_id, (n, *_ ) in SPEC.items()}


def test_no_experiment_is_lost(tidy):
    assert len(tidy) == sum(n for n, *_ in SPEC.values()), "rows were dropped (the fault-free file has no label columns)"
    assert "anomaly-free/anomaly-free" in set(tidy["experiment_id"])
    assert not tidy[["anomaly", "changepoint", *CANONICAL_SENSORS]].isna().any().any()


def test_tidy_columns_and_family(tidy):
    assert list(tidy.columns[: len(TIDY_COLUMNS)]) == TIDY_COLUMNS or set(TIDY_COLUMNS) <= set(tidy.columns)
    family = tidy.groupby("experiment_id")["family"].agg(lambda s: set(s))
    assert family["valve1/10"] == {"valve1"} and family["anomaly-free/anomaly-free"] == {"anomaly-free"}


def test_t_is_a_per_experiment_time_index(tidy):
    tidy = tidy.reset_index(drop=True)
    for experiment_id, g in tidy.groupby("experiment_id"):
        assert g["t"].tolist() == list(range(len(g))), f"t must run 0..n-1 within {experiment_id}"
        assert g["datetime"].is_monotonic_increasing, f"{experiment_id} is not in time order"
        assert g.index.max() - g.index.min() == len(g) - 1, (
            f"rows of {experiment_id} are interleaved with another experiment "
            "(two experiments can overlap in wall-clock time; never sort the whole table by datetime alone)")


def test_load_raw_errors(data_module, tmp_path):
    with pytest.raises(FileNotFoundError):
        data_module.load_raw(tmp_path / "absent")
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError):
        data_module.load_raw(tmp_path / "empty")


def test_summary_command(run_cli, raw_dir, tmp_path):
    result = run_cli(["summary", "--raw-dir", raw_dir], cwd=tmp_path)
    assert result.returncode == 0, result.stderr[-800:]
    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("stdout must be exactly one JSON document (send diagnostics to stderr):\n" + result.stdout[:300])
    assert out["n_experiments"] == len(SPEC)
    assert out["n_rows"] == sum(n for n, *_ in SPEC.values())
    by_id = {e["experiment_id"]: e for e in out["experiments"]}
    assert set(by_id) == set(SPEC)
    assert by_id["valve1/10"]["n_rows"] == 30 and by_id["valve1/10"]["family"] == "valve1"
    assert by_id["valve1/10"]["anomaly_fraction"] == pytest.approx(0.5)
    assert by_id["other/3"]["anomaly_fraction"] == pytest.approx(7 / 13)
    assert by_id["anomaly-free/anomaly-free"]["anomaly_fraction"] == 0.0


def test_summary_command_bad_directory(run_cli, tmp_path):
    result = run_cli(["summary", "--raw-dir", tmp_path / "absent"], cwd=tmp_path)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, "a user error should be a one-line message, not a traceback"
    assert result.stdout.strip() == ""
