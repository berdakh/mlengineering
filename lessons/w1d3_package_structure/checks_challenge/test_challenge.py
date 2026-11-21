"""Acceptance checks for the w1d3 independent challenge (see challenge/README.md)."""
import json
import tomllib

import pandas as pd
import pytest

GOLDEN = {"auc": 0.9992283950617284, "ap": 0.9970760233918129, "acc": 0.9666666666666667, "f1": 0.9090909090909091}
FEATURE_TABLE_COLUMNS = {"unit_id", "window_id", "rms", "line_length", "p2p", "bp_low", "bp_high", "ratio", "temp", "label"}


@pytest.fixture(scope="module")
def feature_file(run_cli, data_csv, tmp_path_factory):
    work = tmp_path_factory.mktemp("features")
    out = work / "artifacts" / "v1" / "features.csv"   # parent directories do not exist yet
    proc = run_cli(["features", "--data", data_csv, "--out", out], cwd=work)
    assert proc.returncode == 0, f"`features` failed:\n{proc.stderr[-800:]}"
    assert out.is_file(), "`features --out` must create missing parent directories and write the file"
    return out


def test_features_table_contract(feature_file):
    table = pd.read_csv(feature_file)
    assert FEATURE_TABLE_COLUMNS <= set(table.columns), f"missing: {FEATURE_TABLE_COLUMNS - set(table.columns)}"
    assert len(table) == 300 and not table[["unit_id", "window_id"]].duplicated().any()
    assert not any(c.startswith("Unnamed") for c in table.columns), "do not write the DataFrame index"
    first = table[(table.unit_id == "P01") & (table.window_id == 0)].iloc[0]
    assert first["rms"] == pytest.approx(0.713007, abs=1e-5)


def test_train_from_features_matches_train_from_raw(run_cli, feature_file, data_csv, tmp_path):
    from_features = run_cli(["train", "--features", feature_file], cwd=tmp_path)
    from_raw = run_cli(["train", "--data", data_csv], cwd=tmp_path)
    assert from_features.returncode == 0, from_features.stderr[-800:]
    assert from_raw.returncode == 0, from_raw.stderr[-800:]
    a, b = json.loads(from_features.stdout), json.loads(from_raw.stdout)
    for key, expected in GOLDEN.items():
        assert a[key] == pytest.approx(expected, abs=1e-6), f"{key} from the saved features drifted"
        assert b[key] == pytest.approx(expected, abs=1e-6)


def test_train_requires_exactly_one_source(run_cli, feature_file, data_csv, tmp_path):
    neither = run_cli(["train"], cwd=tmp_path)
    both = run_cli(["train", "--data", data_csv, "--features", feature_file], cwd=tmp_path)
    assert neither.returncode != 0, "`train` with no input must be a usage error"
    assert both.returncode != 0, "`train` with both --data and --features is ambiguous and must be rejected"


def test_python_dash_m_matches_console_script(run_cli, feature_file, tmp_path):
    proc = run_cli(["train", "--features", feature_file], cwd=tmp_path, how="module")
    assert proc.returncode == 0, f"`python -m pumpwatch` failed:\n{proc.stderr[-800:]}"
    assert json.loads(proc.stdout)["auc"] == pytest.approx(GOLDEN["auc"], abs=1e-6)


@pytest.mark.parametrize("args", [
    ["features", "--data", "missing.csv", "--out", "f.csv"],
    ["train", "--features", "missing.csv"],
    ["train", "--data", "missing.csv"],
])
def test_missing_inputs_are_clean_errors(run_cli, tmp_path, args):
    proc = run_cli(args, cwd=tmp_path)
    assert proc.returncode == 2, f"expected exit code 2 for a missing input, got {proc.returncode}"
    assert "Traceback" not in proc.stderr and proc.stderr.strip()
    assert not (tmp_path / "f.csv").exists(), "no output file should be left behind after a failure"


def test_train_rejects_a_file_that_is_not_a_feature_table(run_cli, data_csv, tmp_path):
    proc = run_cli(["train", "--features", data_csv], cwd=tmp_path)   # raw windows, not features
    assert proc.returncode == 2 and "Traceback" not in proc.stderr, (
        "passing the wrong kind of file must be caught at the boundary with a readable message"
    )


def test_version_bumped_consistently(target, run_cli, tmp_path):
    project = tomllib.loads((target / "pyproject.toml").read_text())["project"]
    assert project.get("version") == "0.2.0" or "version" in project.get("dynamic", [])
    proc = run_cli(["--version"], cwd=tmp_path)
    assert proc.returncode == 0 and "0.2.0" in (proc.stdout + proc.stderr)
