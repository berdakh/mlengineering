"""Challenge: sampling gaps within experiments. All inputs are SYNTHETIC."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pandas as pd
import pytest

from conftest import make_raw_frame, write_raw

REQUIRED = ["experiment_id", "gap_start", "gap_end", "gap_seconds"]


def tidy_from(times: dict[str, list[str]]) -> pd.DataFrame:
    rows = []
    for experiment_id, stamps in times.items():
        for t, stamp in enumerate(stamps):
            rows.append({"experiment_id": experiment_id, "family": experiment_id.split("/")[0], "t": t,
                         "datetime": pd.Timestamp(stamp), "anomaly": 0, "changepoint": 0})
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def find_gaps(data_module):
    assert hasattr(data_module, "find_gaps"), "flowguard.data.find_gaps is missing"
    return data_module.find_gaps


def test_one_gap_is_reported_with_both_timestamps(find_gaps):
    tidy = tidy_from({"valve1/0": ["2020-01-01 00:00:00", "2020-01-01 00:00:01", "2020-01-01 00:00:11",
                                   "2020-01-01 00:00:12"]})
    gaps = find_gaps(tidy, max_gap_seconds=5)
    assert set(REQUIRED) <= set(gaps.columns)
    assert len(gaps) == 1
    row = gaps.iloc[0]
    assert row["experiment_id"] == "valve1/0"
    assert float(row["gap_seconds"]) == pytest.approx(10.0), "gap_seconds is a number of seconds"
    assert pd.Timestamp(row["gap_start"]) == pd.Timestamp("2020-01-01 00:00:01")
    assert pd.Timestamp(row["gap_end"]) == pd.Timestamp("2020-01-01 00:00:11")


def test_experiment_boundaries_are_not_gaps(find_gaps):
    tidy = tidy_from({
        "valve1/0": ["2020-01-01 00:00:00", "2020-01-01 00:00:01"],
        "valve1/1": ["2020-01-03 09:00:00", "2020-01-03 09:00:01"],
        "valve1/10": ["2019-12-31 00:00:00", "2019-12-31 00:00:01"],
    })
    gaps = find_gaps(tidy, max_gap_seconds=5)
    assert len(gaps) == 0, "the interval between two different recordings is not a sampling gap"
    assert set(REQUIRED) <= set(gaps.columns), "an empty result still has its columns"


def test_overlapping_experiments_do_not_hide_or_create_gaps(find_gaps):
    """Two recordings that overlap in wall-clock time; only the second has a hole."""
    tidy = tidy_from({
        "other/3": [f"2020-03-01 16:00:{s:02d}" for s in range(0, 30)],
        "other/4": [f"2020-03-01 16:00:{s:02d}" for s in (10, 11, 12, 40, 41)],
    })
    gaps = find_gaps(tidy, max_gap_seconds=5)
    assert gaps["experiment_id"].tolist() == ["other/4"]
    assert float(gaps["gap_seconds"].iloc[0]) == pytest.approx(28.0)


@pytest.mark.parametrize("threshold, expected", [(5, 0), (4.5, 1), (0.5, 2)])
def test_threshold_is_strictly_greater_than(find_gaps, threshold, expected):
    tidy = tidy_from({"other/1": ["2020-01-01 00:00:00", "2020-01-01 00:00:01", "2020-01-01 00:00:06"]})
    assert len(find_gaps(tidy, max_gap_seconds=threshold)) == expected


def test_negative_threshold_is_an_error(find_gaps):
    with pytest.raises(ValueError):
        find_gaps(tidy_from({"other/1": ["2020-01-01 00:00:00", "2020-01-01 00:00:01"]}), max_gap_seconds=-1)


@pytest.fixture(scope="session")
def gappy_raw_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("gappy")
    frame = make_raw_frame(40, "2020-03-09 10:00:00", True, seed=1)
    write_raw(root / "valve1" / "0.csv", frame.drop(index=list(range(10, 20)) + list(range(30, 34))))  # 11 s and 5 s
    write_raw(root / "valve1" / "1.csv", make_raw_frame(20, "2020-03-12 08:00:00", True, seed=2))
    write_raw(root / "anomaly-free" / "anomaly-free.csv", make_raw_frame(25, "2020-02-08 13:00:00", False, seed=3))
    return root


def test_gaps_command(run_cli, gappy_raw_dir, tmp_path):
    result = run_cli(["gaps", "--raw-dir", gappy_raw_dir], cwd=tmp_path)
    assert result.returncode == 0, result.stderr[-800:]
    out = json.loads(result.stdout)
    assert out["n_gaps"] == 1 and len(out["gaps"]) == 1
    gap = out["gaps"][0]
    assert gap["experiment_id"] == "valve1/0" and gap["gap_seconds"] == pytest.approx(11.0)
    assert out["max_gap_seconds"] == pytest.approx(5.0), "the report states the threshold it used"


def test_gaps_command_uses_the_threshold_argument(run_cli, gappy_raw_dir, tmp_path):
    result = run_cli(["gaps", "--raw-dir", gappy_raw_dir, "--max-gap-seconds", "4"], cwd=tmp_path)
    assert result.returncode == 0, result.stderr[-800:]
    out = json.loads(result.stdout)
    assert out["n_gaps"] == 2
    assert sorted(g["gap_seconds"] for g in out["gaps"]) == pytest.approx([5.0, 11.0])
    assert out["max_gap_seconds"] == pytest.approx(4.0)


def test_gaps_command_rejects_bad_input_cleanly(run_cli, gappy_raw_dir, tmp_path):
    for args in (["gaps", "--raw-dir", tmp_path / "absent"],
                 ["gaps", "--raw-dir", gappy_raw_dir, "--max-gap-seconds", "-3"]):
        result = run_cli(args, cwd=tmp_path)
        assert result.returncode != 0 and "Traceback" not in result.stderr and result.stdout.strip() == ""


def test_summary_still_works(run_cli, gappy_raw_dir, tmp_path):
    out = json.loads(run_cli(["summary", "--raw-dir", gappy_raw_dir], cwd=tmp_path).stdout)
    assert out["n_experiments"] == 3


def test_project_tests_cover_the_new_code_and_pass(target, src, tmp_path):
    tests = target / "tests"
    assert any("find_gaps" in p.read_text() for p in tests.glob("test_*.py")), "no test mentions find_gaps"
    env = dict(os.environ, PYTHONPATH=str(src), PYTHONDONTWRITEBYTECODE="1")
    env.pop("WB_TARGET_DIR", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(tests), "-q", "-p", "no:cacheprovider", f"--rootdir={target}"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, (result.stdout + result.stderr)[-1200:]
    assert re.search(r"(\d+) passed", result.stdout)
