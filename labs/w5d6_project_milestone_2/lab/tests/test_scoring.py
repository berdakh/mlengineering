import numpy as np
import pytest


def test_score_known_values(model):
    assert model.score([-1.0, 1.0], [0.0, 2.0, -3.0]) == pytest.approx([0.0, 2.0, 3.0])


def test_population_std(model):
    assert model.score([0.0, 2.0], [4.0]) == pytest.approx([3.0])     # ddof=1 would give 2.12


def test_threshold_inclusive(model):
    assert model.above_threshold(np.array([2.999, 3.0])).tolist() == [False, True]
