"""predict-batch: the command a scheduler runs. SYNTHETIC input files in a temporary directory.

The CLI is run as a subprocess, as a scheduler would run it, with PYTHONPATH=<target>/src.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pytest

from conftest import make_run

MODEL = {"name": "flowguard-test", "version": "2.0.0", "sensor": "flow_rate", "n_burn": 100,
         "threshold": 4.0, "min_duration": 5, "merge_gap": 3}


@pytest.fixture()
def files(tmp_path, fg, batch_df):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    config = fg.inference.Detector(**MODEL).to_config()
    (model_dir / "model.json").write_text(json.dumps(config, indent=2))
    inp = tmp_path / "rows.csv"
    batch_df.to_csv(inp, index=False)
    return {"model": model_dir, "input": inp, "out": tmp_path / "out", "tmp": tmp_path}


def run_cli(target, *args):
    env = dict(os.environ, PYTHONPATH=str(target / "src"), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "flowguard.cli", "predict-batch", *map(str, args)],
                          capture_output=True, text=True, env=env, timeout=120)


def cli(target, f, inp=None, out=None, *extra):
    return run_cli(target, "--model-dir", f["model"], "--input", inp or f["input"], "--out", out or f["out"], *extra)


def read(path):
    return pd.read_csv(path, float_precision="round_trip")


def test_cli_scores_the_file_like_the_object(target, fg, files, batch_df):
    proc = cli(target, files)
    assert proc.returncode == 0, proc.stderr
    pred = read(files["out"] / "predictions.csv")
    assert list(pred.columns) == list(fg.inference.OUTPUT_COLUMNS)
    assert len(pred) == len(batch_df)
    frame, _ = fg.inference.Detector(**MODEL).score_batch(batch_df)
    np.testing.assert_allclose(pred["score"].to_numpy(), frame["score"].to_numpy(), rtol=1e-12, equal_nan=True)
    np.testing.assert_array_equal(pred["alarm"].to_numpy(), frame["alarm"].to_numpy())
    assert (pred["model_version"].astype(str) == "2.0.0").all() and (pred["threshold"] == 4.0).all()


def test_manifest_describes_input_output_and_model(target, files):
    assert cli(target, files).returncode == 0
    manifest = json.loads((files["out"] / "manifest.json").read_text())
    for key in ("format", "input_sha256", "input_rows", "runs", "runs_scored", "runs_failed",
                "model_name", "model_version", "threshold", "predictions_sha256"):
        assert key in manifest, f"manifest.json lacks {key!r}"
    assert manifest["input_sha256"] == hashlib.sha256(files["input"].read_bytes()).hexdigest()
    assert manifest["predictions_sha256"] == hashlib.sha256((files["out"] / "predictions.csv").read_bytes()).hexdigest()
    assert manifest["model_version"] == "2.0.0" and manifest["runs"] == 3 and manifest["runs_failed"] == {}


def test_rerun_is_byte_identical(target, files):
    assert cli(target, files).returncode == 0
    first = {p.name: p.read_bytes() for p in files["out"].iterdir()}
    time.sleep(1.1)                                          # a timestamp in the output would now differ
    assert cli(target, files).returncode == 0
    second = {p.name: p.read_bytes() for p in files["out"].iterdir()}
    assert first == second


def test_output_does_not_depend_on_chunking(target, files):
    assert cli(target, files, None, files["tmp"] / "a", "--chunk-runs", "1").returncode == 0
    assert cli(target, files, None, files["tmp"] / "b", "--chunk-runs", "50").returncode == 0
    for name in ("predictions.csv", "manifest.json"):
        assert (files["tmp"] / "a" / name).read_bytes() == (files["tmp"] / "b" / name).read_bytes()


def test_partial_failure_scores_the_rest_and_exits_3(target, files, batch_df):
    bad = pd.concat([batch_df, make_run("too_short", n=60, seed=21)], ignore_index=True)
    inp = files["tmp"] / "with_bad_run.csv"
    bad.to_csv(inp, index=False)
    proc = cli(target, files, inp)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    manifest = json.loads((files["out"] / "manifest.json").read_text())
    assert list(manifest["runs_failed"]) == ["too_short"] and manifest["runs_scored"] == 3
    pred = read(files["out"] / "predictions.csv")
    assert (pred.loc[pred["run_id"] == "too_short", "status"] == "error").all()
    assert (pred.loc[pred["run_id"] != "too_short", "status"] != "error").all()


def test_schema_error_exits_2_and_writes_nothing(target, files, batch_df):
    inp = files["tmp"] / "labelled.csv"
    batch_df.assign(anomaly=0).to_csv(inp, index=False)
    proc = cli(target, files, inp)
    assert proc.returncode == 2
    assert "anomaly" in proc.stderr
    assert not (files["out"] / "predictions.csv").exists()


def test_existing_output_for_another_input_is_not_overwritten(target, files, batch_df):
    assert cli(target, files).returncode == 0
    before = {p.name: p.read_bytes() for p in files["out"].iterdir()}
    other = files["tmp"] / "other.csv"
    batch_df[batch_df["run_id"] != "r2"].to_csv(other, index=False)
    proc = cli(target, files, other)
    assert proc.returncode == 2
    assert {p.name: p.read_bytes() for p in files["out"].iterdir()} == before
    assert cli(target, files, other, None, "--force").returncode == 0
    manifest = json.loads((files["out"] / "manifest.json").read_text())
    assert manifest["input_sha256"] == hashlib.sha256(other.read_bytes()).hexdigest()


def test_files_are_moved_into_place_atomically(fg, files, monkeypatch):
    moved = []
    real_replace = os.replace

    def recording_replace(src, dst, *a, **k):
        moved.append(os.path.basename(os.fspath(dst)))
        return real_replace(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", recording_replace)
    fg.batch.predict_batch(files["model"], files["input"], files["out"])
    assert {"predictions.csv", "manifest.json"} <= set(moved), (
        "write each output to a temporary file and move it into place with os.replace")
    assert not [p for p in files["out"].iterdir() if p.name not in ("predictions.csv", "manifest.json")], (
        "temporary files were left behind")
