"""A training run leaves behind a self-describing run directory and a clean stdout."""
import hashlib
import json
import platform
from importlib import metadata
from pathlib import Path

from conftest import DATA


def test_run_directory_contains_the_four_artifacts(base_run):
    run_dir = base_run.dir
    for name in ("config.json", "metrics.json", "environment.json"):
        assert (run_dir / name).is_file(), f"missing {name}"
    logs = [p for p in run_dir.glob("*.log") if p.stat().st_size > 0]
    assert logs, "the run directory should contain a non-empty *.log file"


def test_stdout_is_exactly_one_json_object(base_run):
    payload = json.loads(base_run.proc.stdout)          # fails if logs leak onto stdout
    assert {"run_dir", "metrics"} <= set(payload)
    assert Path(payload["run_dir"]).resolve() == base_run.dir.resolve()
    assert payload["metrics"] == base_run.json("metrics.json")


def test_metrics_schema(base_run):
    metrics = base_run.json("metrics.json")
    assert {"auc", "ap", "acc", "f1", "n_train", "n_test", "test_units"} <= set(metrics)
    assert 0.0 <= metrics["auc"] <= 1.0
    assert metrics["n_train"] + metrics["n_test"] == 300


def test_environment_records_code_library_and_data_provenance(base_run):
    env = base_run.json("environment.json")
    assert env["python"] == platform.python_version()
    assert env["packages"]["numpy"] == metadata.version("numpy")
    assert env["packages"]["scikit-learn"] == metadata.version("scikit-learn")
    assert "git_commit" in env                           # may be null outside a git checkout
    assert env["data_sha256"] == hashlib.sha256(DATA.read_bytes()).hexdigest()


def test_each_run_gets_its_own_directory(cli, workdir, base_config):
    parent = workdir / "shared_parent"
    for _ in range(2):
        proc = cli.run("train", "--config", base_config, "--run-dir", parent, cwd=workdir)
        assert proc.returncode == 0, proc.stderr[-800:]
    assert len([p for p in parent.iterdir() if p.is_dir()]) == 2, "a second run must not overwrite the first"


def test_shipped_base_config_runs_from_the_repository_root(cli, target, workdir):
    from conftest import ROOT
    config = target / "configs" / "base.toml"
    assert config.is_file(), "configs/base.toml should ship with the package project"
    proc = cli.run("train", "--config", config, "--run-dir", workdir / "shipped", cwd=ROOT)
    assert proc.returncode == 0, proc.stderr[-800:]
