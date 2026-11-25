from __future__ import annotations

import json

import pandas as pd
import pytest
from conftest import write_experiment

from flowguard.cli import main
from flowguard.data import SENSOR_COLUMNS, TIDY_COLUMNS, load_experiment, load_raw, summarize


def test_load_experiment_renames_by_name_and_types(raw_dir):
    df = load_experiment(raw_dir / "valve1" / "0.csv")
    assert list(df.columns) == ["datetime", *SENSOR_COLUMNS, "anomaly", "changepoint"]
    assert pd.api.types.is_datetime64_any_dtype(df["datetime"])
    assert pd.api.types.is_integer_dtype(df["anomaly"])
    assert df["anomaly"].sum() == 10


def test_load_experiment_is_robust_to_column_order(tmp_path):
    path = tmp_path / "valve1" / "0.csv"
    original = write_experiment(path, 10, "2020-01-01 00:00:00")
    reordered = original[original.columns[::-1]]
    reordered.to_csv(path, sep=";", index=False)
    df = load_experiment(path)
    assert df["flow_rate"].tolist() == pytest.approx(original["Volume Flow RateRMS"].tolist())
    assert df["current"].tolist() == pytest.approx(original["Current"].tolist())


def test_load_experiment_sorts_by_time(raw_dir):
    df = load_experiment(raw_dir / "valve1" / "2.csv")
    assert df["datetime"].is_monotonic_increasing


def test_unlabelled_file_gets_zero_labels(raw_dir):
    df = load_experiment(raw_dir / "anomaly-free" / "anomaly-free.csv")
    assert len(df) == 40
    assert df["anomaly"].eq(0).all() and df["changepoint"].eq(0).all()


def test_missing_column_is_named(tmp_path):
    path = tmp_path / "valve1" / "0.csv"
    write_experiment(path, 5, "2020-01-01 00:00:00").drop(columns=["Pressure"]).to_csv(
        path, sep=";", index=False
    )
    with pytest.raises(ValueError, match="Pressure"):
        load_experiment(path)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_experiment(tmp_path / "nope.csv")


def test_ids_come_from_file_names_not_positions(raw_dir):
    tidy = load_raw(raw_dir)
    sizes = tidy.groupby("experiment_id").size().to_dict()
    assert sizes == {
        "valve1/0": 20,
        "valve1/2": 22,
        "valve1/10": 30,
        "other/1": 12,
        "anomaly-free/anomaly-free": 40,
    }


def test_tidy_layout(raw_dir):
    tidy = load_raw(raw_dir)
    assert list(tidy.columns) == list(TIDY_COLUMNS)
    for _, g in tidy.groupby("experiment_id"):
        assert g["t"].tolist() == list(range(len(g)))
        assert g["datetime"].is_monotonic_increasing
        assert g.index.max() - g.index.min() == len(g) - 1  # one contiguous block
    assert tidy.loc[tidy.experiment_id == "valve1/10", "family"].eq("valve1").all()


def test_load_raw_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_raw(tmp_path / "absent")
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError):
        load_raw(tmp_path / "empty")


def test_summarize(raw_dir):
    s = summarize(load_raw(raw_dir))
    assert s["n_experiments"] == 5 and s["n_rows"] == 124
    by_id = {e["experiment_id"]: e for e in s["experiments"]}
    assert by_id["valve1/10"]["anomaly_fraction"] == pytest.approx(0.5)
    assert by_id["anomaly-free/anomaly-free"]["anomaly_fraction"] == 0.0
    json.dumps(s)  # plain types only


def test_cli_summary_prints_only_json(raw_dir, capsys):
    assert main(["summary", "--raw-dir", str(raw_dir)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["n_experiments"] == 5


def test_cli_bad_dir_exit_code(tmp_path, capsys):
    assert main(["summary", "--raw-dir", str(tmp_path / "absent")]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "absent" in captured.err
