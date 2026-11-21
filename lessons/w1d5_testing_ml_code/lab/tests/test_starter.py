"""Starter tests. They pass - and they would keep passing with most bugs present.

Replace them. Run from this lab directory:

    cd lessons/w1d5_testing_ml_code/lab
    python -m pytest tests -q
"""
import numpy as np

from pumpwatch.features import rms, window_features


def test_rms_runs():
    x = np.random.randn(128)
    assert rms(x) > 0


def test_window_features_has_keys():
    feats = window_features(np.random.randn(128), fs=256.0)
    assert set(feats) == {"rms", "line_length", "p2p", "bp_low", "bp_high", "ratio"}
