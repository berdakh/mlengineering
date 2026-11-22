"""A parity test that only checks shapes and that scores are finite."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from serve_scores import score_run
from train_features import training_scores

MODEL = json.loads((Path(__file__).resolve().parent / "model" / "logistic.json").read_text())


def test_same_length_and_finite():
    rng = np.random.default_rng(0)
    run = pd.DataFrame({s: rng.normal(10, 1, 240) for s in MODEL["sensors"]})
    served, trained = score_run(run, MODEL), training_scores(run, MODEL)
    assert len(served) == len(trained)
    assert np.isfinite(served).all()
