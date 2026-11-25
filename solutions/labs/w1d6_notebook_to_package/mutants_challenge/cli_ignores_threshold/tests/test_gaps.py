from __future__ import annotations

import json

import pandas as pd
import pytest
from conftest import write_experiment

from flowguard.cli import main
from flowguard.data import GAP_COLUMNS, find_gaps, load_raw


def tidy_from(times: dict[str, list[str]]) -> pd.DataFrame:
    """Minimal tidy frame: only the columns find_gaps is allowed to depend on."""
    rows = []
    for experiment_id, stamps in times.items():
        for t, stamp in enumerate(stamps):
            rows.append({"experiment_id": experiment_id, "t": t, "datetime": pd.Timestamp(stamp)})
    return pd.DataFrame(rows)


def test_gap_inside_one_experiment():
    tidy = tidy_from({"valve1/0": ["2020-01-01 00:00:00", "2020-01-01 00:00:01", "2020-01-01 00:00:11"]})
    gaps = find_gaps(tidy, max_gap_seconds=5)
    assert list(gaps.columns) == list(GAP_COLUMNS)
    assert len(gaps) == 1
    row = gaps.iloc[0]
    assert (row.experiment_id, row.t, row.gap_seconds) == ("valve1/0", 2, 10.0)
    assert row.gap_start == pd.Timestamp("2020-01-01 00:00:01") and row.gap_end == pd.Timestamp("2020-01-01 00:00:11")


def test_boundary_between_experiments_is_not_a_gap():
    tidy = tidy_from({
        "valve1/0": ["2020-01-01 00:00:00", "2020-01-01 00:00:01"],
        "valve1/1": ["2020-01-03 09:00:00", "2020-01-03 09:00:01"],      # two days later
        "valve1/2": ["2019-12-31 00:00:00", "2019-12-31 00:00:01"],      # earlier than both
    })
    assert find_gaps(tidy, max_gap_seconds=5).empty


@pytest.mark.parametrize("threshold, expected", [(5, 0), (4.999, 1), (0, 2)])
def test_threshold_is_strict(threshold, expected):
    tidy = tidy_from({"other/1": ["2020-01-01 00:00:00", "2020-01-01 00:00:01", "2020-01-01 00:00:06"]})
    assert len(find_gaps(tidy, max_gap_seconds=threshold)) == expected


def test_no_gaps_gives_empty_frame_with_columns():
    tidy = tidy_from({"other/1": ["2020-01-01 00:00:00", "2020-01-01 00:00:01"]})
    gaps = find_gaps(tidy)
    assert gaps.empty and list(gaps.columns) == list(GAP_COLUMNS)


def test_negative_threshold_rejected():
    with pytest.raises(ValueError):
        find_gaps(tidy_from({"other/1": ["2020-01-01 00:00:00"]}), max_gap_seconds=-1)


def test_cli_gaps(tmp_path, capsys):
    root = tmp_path / "skab"
    frame = write_experiment(root / "valve1" / "0.csv", 20, "2020-03-09 10:00:00")
    frame.drop(index=range(5, 15)).to_csv(root / "valve1" / "0.csv", sep=";", index=False)   # 11 s hole
    write_experiment(root / "valve1" / "1.csv", 20, "2020-03-10 10:00:00")
    assert main(["gaps", "--raw-dir", str(root)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["n_gaps"] == 1 and out["gaps"][0]["experiment_id"] == "valve1/0"
    assert out["gaps"][0]["gap_seconds"] == 11.0
    assert load_raw(root)["experiment_id"].nunique() == 2
