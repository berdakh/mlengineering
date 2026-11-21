"""`flowguard features`: deterministic, content-addressed output."""
from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

import synth


@pytest.fixture(scope="module")
def work(tmp_path_factory):
    d = tmp_path_factory.mktemp("w2d5_cache")
    synth.make_tidy().to_csv(d / "tidy.csv", index=False)
    return d


def _features(run_cli, work, *extra, data="tidy.csv", out="cache"):
    proc = run_cli("features", "--data", work / data, "--out-dir", work / out, *extra, cwd=work)
    assert proc.returncode == 0, f"features command failed:\n{proc.stderr[-1500:]}"
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert {"key", "path", "cache_hit"} <= set(payload), "stdout must end with a JSON object: key, path, cache_hit"
    return payload


def test_first_run_writes_table_and_metadata(run_cli, work):
    first = _features(run_cli, work, "--windows", 5, 12)
    assert first["cache_hit"] is False
    table = pd.read_csv(first["path"])
    assert len(table) == len(synth.make_tidy())
    assert "current__mean_5" in table.columns and "flow_rate__slope_12" in table.columns
    meta_path = work / "cache" / first["key"][:16] / "meta.json"
    assert meta_path.is_file(), "expected <out-dir>/<first 16 hex chars of key>/meta.json"
    meta = json.loads(meta_path.read_text())
    assert meta["key"] == first["key"] and meta["n_rows"] == len(table)
    assert meta["data_sha256"] == hashlib.sha256((work / "tidy.csv").read_bytes()).hexdigest()
    assert sorted(meta["params"]["windows"]) == [5, 12]


def test_same_inputs_hit_the_cache_and_do_not_rewrite(run_cli, work):
    first = _features(run_cli, work, "--windows", 5, 12)
    stamp = (work / "cache" / first["key"][:16] / "features.csv").stat().st_mtime_ns
    again = _features(run_cli, work, "--windows", 12, 5)  # order of windows is not a different request
    assert again["key"] == first["key"] and again["cache_hit"] is True
    assert (work / "cache" / first["key"][:16] / "features.csv").stat().st_mtime_ns == stamp


def test_recomputation_is_byte_identical(run_cli, work):
    a = _features(run_cli, work, "--windows", 5, 12, out="cache_a")
    b = _features(run_cli, work, "--windows", 5, 12, out="cache_b")
    assert a["key"] == b["key"]
    assert open(a["path"], "rb").read() == open(b["path"], "rb").read()


@pytest.mark.parametrize("extra", [("--windows", 5, 13), ("--windows", 5, 12, "--max-gap-s", 600)])
def test_changed_parameter_changes_the_key(run_cli, work, extra):
    base = _features(run_cli, work, "--windows", 5, 12)
    other = _features(run_cli, work, *extra)
    assert other["key"] != base["key"], "a different parameter produced the same cache key: stale features would be served"
    assert other["path"] != base["path"]


def test_changed_data_changes_the_key(run_cli, work):
    base = _features(run_cli, work, "--windows", 5, 12)
    tidy = synth.make_tidy()
    tidy.loc[3, "pressure"] += 0.001
    tidy.to_csv(work / "tidy_edited.csv", index=False)
    edited = _features(run_cli, work, "--windows", 5, 12, data="tidy_edited.csv")
    assert edited["key"] != base["key"]


def test_missing_data_file_is_a_clean_error(run_cli, work):
    proc = run_cli("features", "--data", work / "nope.csv", "--out-dir", work / "cache", cwd=work)
    assert proc.returncode != 0 and "Traceback" not in proc.stderr
