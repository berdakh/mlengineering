"""Candidate generation: grids and reproducible random sampling."""
import math

import numpy as np
import pytest

SPACE = {"C": ("loguniform", 1e-3, 1e3), "depth": ("int", 2, 5), "kind": ("choice", ["a", "b", "c"]),
         "frac": ("uniform", 0.2, 0.8)}


def test_param_grid_is_the_full_product(sel):
    grid = sel.param_grid({"a": [1, 2, 3], "b": ["x", "y"]})
    assert len(grid) == 6
    assert {(g["a"], g["b"]) for g in grid} == {(a, b) for a in (1, 2, 3) for b in ("x", "y")}
    assert grid == sel.param_grid({"a": [1, 2, 3], "b": ["x", "y"]}), "grid order must be deterministic"


def test_sample_params_is_reproducible_and_seed_dependent(sel):
    a, b, c = sel.sample_params(SPACE, 20, seed=3), sel.sample_params(SPACE, 20, seed=3), sel.sample_params(SPACE, 20, seed=4)
    assert a == b, "the same seed must give the same candidates"
    assert a != c, "a different seed must give different candidates"
    assert len(a) == 20 and all(set(p) == set(SPACE) for p in a)


def test_sample_params_respects_bounds_and_types(sel):
    cands = sel.sample_params(SPACE, 400, seed=0)
    assert all(1e-3 <= p["C"] <= 1e3 for p in cands)
    assert all(0.2 <= p["frac"] <= 0.8 for p in cands)
    assert all(p["kind"] in ("a", "b", "c") for p in cands)
    depths = {p["depth"] for p in cands}
    assert all(float(d).is_integer() for d in depths)
    assert depths == {2, 3, 4, 5}, "integer bounds are inclusive at both ends"


def test_loguniform_is_uniform_in_the_exponent(sel):
    """Half the draws fall below the geometric mean, and every decade gets about the same share."""
    values = np.array([p["C"] for p in sel.sample_params({"C": ("loguniform", 1e-3, 1e3)}, 3000, seed=1)])
    assert abs(np.mean(values < 1.0) - 0.5) < 0.04, "a linear-uniform draw puts ~0.1% below 1.0"
    per_decade = np.histogram(np.log10(values), bins=6, range=(-3, 3))[0] / len(values)
    assert per_decade.min() > 0.12 and per_decade.max() < 0.21


def test_unknown_distribution_is_an_error(sel):
    with pytest.raises(ValueError):
        sel.sample_params({"C": ("gaussian", 0, 1)}, 3, seed=0)
    assert math.isfinite(1.0)
