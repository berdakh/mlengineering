"""Smoke/integration test of the training path.

This is NOT a model-quality test. The data are constructed so that the classes are
separated by a huge margin; any correctly wired pipeline scores AUC = 1.0. The
assertion `auc >= 0.9` therefore detects wiring defects (wrong probability column,
shuffled labels, features misaligned with labels) and is deterministic: fixed data
seed, fixed split seed, deterministic solver.
"""
import math

from signals import FS
from pumpwatch.features import build_feature_table
from pumpwatch.model import train_and_evaluate


def test_train_and_evaluate_contract(make_frame):
    features = build_feature_table(make_frame(), FS)
    metrics = train_and_evaluate(features, test_fraction=0.34, seed=0)
    assert {"n_train", "n_test", "test_units", "auc", "ap", "acc", "f1"} <= set(metrics)
    assert metrics["n_train"] + metrics["n_test"] == len(features)
    train_units = set(features["unit_id"]) - set(metrics["test_units"])
    assert train_units and train_units.isdisjoint(metrics["test_units"])
    for key in ("auc", "ap", "acc", "f1"):
        assert isinstance(metrics[key], float) and math.isfinite(metrics[key])
        assert 0.0 <= metrics[key] <= 1.0


def test_pipeline_learns_a_trivially_separable_problem(make_frame):
    features = build_feature_table(make_frame(), FS)
    metrics = train_and_evaluate(features, test_fraction=0.34, seed=0)
    assert metrics["auc"] >= 0.9


def test_training_is_deterministic(make_frame):
    features = build_feature_table(make_frame(), FS)
    assert train_and_evaluate(features, seed=3) == train_and_evaluate(features, seed=3)
