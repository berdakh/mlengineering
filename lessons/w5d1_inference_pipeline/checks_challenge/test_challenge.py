"""w5d1 challenge: the serving path reproduces the training path, the learner's parity test would have
caught every planted bug, and the skew report is written. SYNTHETIC runs."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import numpy as np
import pytest

from conftest import HERE, MODEL, UNIT_DIR, make_run, oracle


@pytest.mark.parametrize("seed, shift, sensor", [(0, 0.0, -1), (1, 3.0, -1), (2, -4.0, 2), (3, 2.0, 0)])
def test_serving_matches_training_on_ordinary_runs(serve, seed, shift, sensor):
    run = make_run(seed=seed, shift=shift, sensor=sensor)
    np.testing.assert_allclose(serve.score_run(run, MODEL), oracle(run, MODEL), rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("sensor", [-1, 3])
def test_serving_matches_training_beyond_the_clip(serve, sensor):
    run = make_run(seed=5, shift=400.0, sensor=sensor)
    np.testing.assert_allclose(serve.score_run(run, MODEL), oracle(run, MODEL), rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("n_burn", [60, 80, 100, 140])
def test_serving_takes_the_burn_in_from_the_model(serve, n_burn):
    model = dict(MODEL, n_burn=n_burn)
    run = make_run(seed=6, shift=3.0)
    served = serve.score_run(run, model)
    assert len(served) == len(run) - n_burn
    np.testing.assert_allclose(served, oracle(run, model), rtol=1e-12, atol=1e-12)


def run_learner_test(target, tmp_path, serving_source):
    """Run <target>/test_parity.py in a scratch copy, with serve_scores.py replaced by ``serving_source``."""
    work = tmp_path / "work"
    work.mkdir()
    shutil.copy(target / "test_parity.py", work / "test_parity.py")
    shutil.copy(serving_source, work / "serve_scores.py")
    shutil.copy(UNIT_DIR / "challenge" / "train_features.py", work / "train_features.py")   # the given training path
    shutil.copytree(UNIT_DIR / "challenge" / "model", work / "model")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_parity.py"],
                          cwd=work, capture_output=True, text=True, env=env, timeout=120)


def test_parity_test_exists_and_passes_on_the_fixed_serving_path(target, tmp_path):
    assert (target / "test_parity.py").is_file(), "write test_parity.py next to serve_scores.py"
    proc = run_learner_test(target, tmp_path, target / "serve_scores.py")
    assert proc.returncode == 0, proc.stdout[-2000:]
    assert re.search(r"\d+ passed", proc.stdout)


@pytest.mark.parametrize("variant", ["original.py", "bug_burnin.py", "bug_clip.py", "bug_order.py"])
def test_parity_test_fails_on_each_planted_bug(target, tmp_path, variant):
    assert (target / "test_parity.py").is_file(), "write test_parity.py next to serve_scores.py"
    proc = run_learner_test(target, tmp_path, HERE / "variants" / variant)
    assert proc.returncode == 1, (
        f"your test_parity.py passes against a serving path with the bug in variants/{variant}; "
        "it would not have caught it")


def test_skew_report_is_written(target):
    path = target / "SKEW_REPORT.md"
    assert path.is_file(), "missing SKEW_REPORT.md"
    text = path.read_text()
    assert "TODO" not in text, "SKEW_REPORT.md still contains TODO"
    sections = re.findall(r"^##\s+\S", text, flags=re.M)
    assert len(sections) >= 3, "describe each of the three bugs under its own '## ' heading"
    assert len(text.split()) >= 150, "the report is too short to explain three bugs and their tests"
