"""Parity test: the serving path must reproduce the training path (reference solution).

Run from this directory:  python -m pytest test_parity.py -q
SYNTHETIC runs only. Each case is built to expose one kind of skew.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from serve_scores import score_run
from train_features import training_scores

HERE = Path(__file__).resolve().parent
MODEL = json.loads((HERE / "model" / "logistic.json").read_text())


def make_run(n=240, seed=0, shift=0.0):
    rng = np.random.default_rng(seed)
    data = {s: rng.normal(10 + i, 1 + 0.1 * i, n) for i, s in enumerate(MODEL["sensors"])}
    run = pd.DataFrame(data)
    run.loc[150:, MODEL["sensors"][-1]] += shift          # a fault on flow rate after row 150
    return run


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_matches_training_path_on_ordinary_runs(seed):
    run = make_run(seed=seed, shift=3.0)
    np.testing.assert_allclose(score_run(run, MODEL), training_scores(run, MODEL), rtol=1e-12, atol=1e-12)


def test_matches_when_values_hit_the_clip():
    run = make_run(shift=500.0)                           # |z| far beyond z_clip
    np.testing.assert_allclose(score_run(run, MODEL), training_scores(run, MODEL), rtol=1e-12, atol=1e-12)


def test_burn_in_length_comes_from_the_model():
    model = dict(MODEL, n_burn=80)
    run = make_run(shift=3.0)
    served = score_run(run, model)
    assert len(served) == len(run) - 80
    np.testing.assert_allclose(served, training_scores(run, model), rtol=1e-12, atol=1e-12)
