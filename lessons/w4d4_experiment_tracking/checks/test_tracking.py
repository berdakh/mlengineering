"""Behavioural checks for flowguard.tracking (SYNTHETIC task only; no SKAB data needed)."""
from __future__ import annotations

import json
import shutil

import pandas as pd
import pytest

from conftest import cli, spec, spec_toml  # noqa: F401


# ------------------------------------------------------------------ Task 1: identity
def test_hash_ignores_key_order_and_sees_every_value(tr):
    a = {"model": {"alpha": 1.0, "kind": "ridge"}, "data": {"noise": 1.0}, "seed": 0, "task": "synthetic"}
    b = {"seed": 0, "task": "synthetic", "data": {"noise": 1.0}, "model": {"kind": "ridge", "alpha": 1.0}}
    assert tr.config_hash(a) == tr.config_hash(b), "the same configuration must have the same id"
    c = json.loads(json.dumps(a))
    c["model"]["alpha"] = 2.0
    assert tr.config_hash(c) != tr.config_hash(a)
    d = json.loads(json.dumps(a))
    d["seed"] = 1
    assert tr.config_hash(d) != tr.config_hash(a), "runs that differ only in seed are different runs"
    assert tr.config_hash(a) == tr.config_hash(json.loads(json.dumps(a))), "must be stable across calls"


# ------------------------------------------------------------------ Task 2: expansion
def test_grid_expansion_count_uniqueness_and_content(tr):
    configs = tr.expand_sweep(spec())
    assert len(configs) == 2 * 2 * 3
    assert len({tr.config_hash(c) for c in configs}) == 12, "every run must have its own id"
    assert {(c["model"]["alpha"], c["data"]["noise"], c["seed"]) for c in configs} == {
        (a, n, s) for a in (0.1, 10.0) for n in (1.0, 2.0) for s in (0, 1, 2)}
    assert all(c["data"]["n_rows"] == 120 and c["task"] == "synthetic" and c["sweep"] == "ridge" for c in configs)
    assert configs == tr.expand_sweep(spec()), "expansion must be deterministic"


def test_expansion_does_not_share_mutable_state(tr):
    configs = tr.expand_sweep(spec())
    configs[0]["data"]["n_rows"] = -1
    assert configs[1]["data"]["n_rows"] == 120, "configs must be independent copies of the base"


def test_random_expansion(tr):
    s = {"sweep": {"name": "r", "task": "synthetic", "mode": "random", "seeds": [0, 1], "n_samples": 6,
                   "sample_seed": 3},
         "base": {"data": {"n_rows": 100}},
         "space": {"model": {"alpha": {"dist": "loguniform", "low": 0.01, "high": 100.0}}}}
    configs = tr.expand_sweep(s)
    assert len(configs) == 12
    alphas = sorted({c["model"]["alpha"] for c in configs})
    assert len(alphas) == 6 and all(0.01 <= a <= 100.0 for a in alphas)
    assert tr.expand_sweep(s) == configs, "same sample_seed, same draws"
    s2 = json.loads(json.dumps(s))
    s2["sweep"]["sample_seed"] = 4
    assert {c["model"]["alpha"] for c in tr.expand_sweep(s2)} != set(alphas)


# ------------------------------------------------------------------ Task 3: execute
def test_execute_writes_a_complete_run_directory(tr, tmp_path):
    config = tr.expand_sweep(spec())[0]
    result = tr.execute(config, tmp_path)
    run_dir = tmp_path / result["run_id"]
    assert result["status"] == "complete" and result["run_id"] == tr.config_hash(config)
    assert json.loads((run_dir / "config.json").read_text()) == config
    env = json.loads((run_dir / "environment.json").read_text())
    assert "python" in env and "packages" in env
    assert set(json.loads((run_dir / "metrics.json").read_text())) == {"mse", "r2"}
    assert json.loads((run_dir / "status.json").read_text())["status"] == "complete"


def test_complete_runs_are_never_rerun_or_overwritten(tr, tmp_path):
    config = tr.expand_sweep(spec())[0]
    first = tr.execute(config, tmp_path)
    metrics = tmp_path / first["run_id"] / "metrics.json"
    before = metrics.read_bytes()
    metrics.write_text(json.dumps({"mse": 123.0, "r2": -1.0}))     # pretend history; must survive
    again = tr.execute(config, tmp_path)
    assert again["status"] == "skipped" and again["run_id"] == first["run_id"]
    assert json.loads(metrics.read_text())["mse"] == 123.0, "a completed run directory was rewritten"
    assert before != metrics.read_bytes()


def test_failing_task_is_recorded_not_raised(tr, tmp_path):
    config = tr.expand_sweep(spec(fail=True))[0]
    result = tr.execute(config, tmp_path)
    status = json.loads((tmp_path / result["run_id"] / "status.json").read_text())
    assert result["status"] == "failed" and status["status"] == "failed"
    assert "fail" in json.dumps(status).lower(), "record the error message"


# ------------------------------------------------------------------ Task 4: index
def _sweep_into(tr, runs, s):
    return [tr.execute(c, runs) for c in tr.expand_sweep(s)]


def test_index_has_one_row_per_run_and_the_right_columns(tr, tmp_path):
    _sweep_into(tr, tmp_path, spec())
    index = tr.build_index(tmp_path)
    assert len(index) == 12 and set(index["status"]) == {"complete"}
    for col in ("run_id", "status", "seed", "sweep", "param.model.alpha", "param.data.noise", "metric.mse"):
        assert col in index.columns, f"missing column {col}"
    assert set(index["run_id"]) == {p.name for p in tmp_path.iterdir() if p.is_dir()}


def test_partial_and_failed_runs_are_labelled(tr, tmp_path):
    results = _sweep_into(tr, tmp_path, spec())
    crashed = tmp_path / results[0]["run_id"]
    (crashed / "status.json").unlink()                     # died after writing metrics, before status
    failed = tr.execute(tr.expand_sweep(spec(fail=True))[0], tmp_path)
    index = tr.build_index(tmp_path).set_index("run_id")
    assert index.loc[results[0]["run_id"], "status"] == "partial", (
        "a run without status.json did not finish: it is partial even if metrics.json exists")
    assert index.loc[failed["run_id"], "status"] == "failed"


def test_index_is_rebuilt_from_disk_not_read_back(tr, tmp_path):
    results = _sweep_into(tr, tmp_path, spec())
    tr.write_index(tmp_path)
    shutil.rmtree(tmp_path / results[0]["run_id"])
    index = tr.build_index(tmp_path)
    assert len(index) == 11 and results[0]["run_id"] not in set(index["run_id"]), (
        "the run directories are the source of truth; index.csv is only a derived copy")


# ------------------------------------------------------------------ Task 5: aggregate
def test_aggregate_statistics_over_seeds(tr, tmp_path):
    _sweep_into(tr, tmp_path, spec())
    index = tr.build_index(tmp_path)
    table = tr.aggregate(index, "mse")
    assert len(table) == 4 and set(table["n"]) == {3}
    for _, row in table.iterrows():
        group = index[(index["param.model.alpha"] == row["param.model.alpha"])
                      & (index["param.data.noise"] == row["param.data.noise"])]["metric.mse"]
        assert row["mean"] == pytest.approx(group.mean())
        assert row["sd"] == pytest.approx(group.std(ddof=1)), "sample sd over seeds (ddof = 1)"


def test_aggregate_excludes_and_counts_unfinished_runs(tr, tmp_path):
    results = _sweep_into(tr, tmp_path, spec())
    (tmp_path / results[0]["run_id"] / "status.json").unlink()
    index = tr.build_index(tmp_path)
    table = tr.aggregate(index, "mse")
    assert sorted(table["n"]) == [2, 3, 3, 3], "the partial run must not be averaged in"
    assert int(table["excluded"].sum()) == 1, "and it must be visible as excluded"


def test_aggregate_keeps_sweeps_with_different_parameters(tr, tmp_path):
    _sweep_into(tr, tmp_path, spec())
    other = spec(name="other", alphas=(1.0,), noises=(1.0,))
    other["base"]["data"]["extra"] = 5                       # a parameter the first sweep does not have
    _sweep_into(tr, tmp_path, other)
    table = tr.aggregate(tr.build_index(tmp_path), "mse")
    assert set(table["sweep"]) == {"ridge", "other"}, (
        "configurations whose parameter columns are partly empty (NaN) were dropped by the grouping")
    assert int(table["n"].sum()) == 15


# ------------------------------------------------------------------ Task 6: reproduce
def test_reproduce_matches_a_fresh_run_and_catches_tampering(tr, tmp_path):
    result = _sweep_into(tr, tmp_path, spec())[0]
    out = tr.reproduce(result["run_id"], tmp_path)
    assert out["match"] is True and out["max_abs_diff"] == pytest.approx(0.0, abs=1e-12)
    metrics = tmp_path / result["run_id"] / "metrics.json"
    stored = json.loads(metrics.read_text())
    stored["mse"] += 0.01
    metrics.write_text(json.dumps(stored))
    out = tr.reproduce(result["run_id"], tmp_path)
    assert out["match"] is False, "reproduce must re-run the config, not compare the stored file with itself"
    assert out["max_abs_diff"] == pytest.approx(0.01, rel=1e-6)


def test_reproduce_refuses_unfinished_runs(tr, tmp_path):
    result = _sweep_into(tr, tmp_path, spec())[0]
    (tmp_path / result["run_id"] / "status.json").unlink()
    with pytest.raises(ValueError):
        tr.reproduce(result["run_id"], tmp_path)


# ------------------------------------------------------------------ CLI end to end
def test_cli_sweep_table_and_rerun(tmp_path):
    spec_file = spec_toml(tmp_path / "s.toml")
    first = cli("sweep", "--spec", str(spec_file), "--runs-dir", "runs", cwd=tmp_path)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout.strip().splitlines()[-1])["complete"] == 6
    index_csv = pd.read_csv(tmp_path / "runs" / "index.csv")
    assert len(index_csv) == 6
    second = cli("sweep", "--spec", str(spec_file), "--runs-dir", "runs", cwd=tmp_path)
    assert json.loads(second.stdout.strip().splitlines()[-1])["skipped"] == 6, "nothing should be rerun"
    table = cli("runs", "table", "--runs-dir", "runs", "--metric", "mse", cwd=tmp_path)
    assert table.returncode == 0, table.stderr
    assert table.stdout.count("| ridge |") == 2


def test_cli_reports_failures_with_exit_code(tmp_path):
    spec_file = spec_toml(tmp_path / "s.toml", extra_data="fail = true")
    out = cli("sweep", "--spec", str(spec_file), "--runs-dir", "runs", cwd=tmp_path)
    assert out.returncode == 1 and json.loads(out.stdout.strip().splitlines()[-1])["failed"] == 6
