"""Lab task 1: guards.out_of_support, guards.fallback_alarms, guards.all_finite."""
from __future__ import annotations

import math

import numpy as np


def test_out_of_support_inclusive_bounds(fg):
    g = fg["guards"]
    assert g.out_of_support([5.0, 0.0, 10.0, -0.1, 10.1, 7.0], 0.0, 10.0) == [3, 4]
    assert g.out_of_support([], 0.0, 10.0) == []


def test_out_of_support_accepts_numpy(fg):
    assert fg["guards"].out_of_support(np.array([1.0, 50.0]), 0.0, 10.0) == [1]


def test_fallback_alarms_one_bool_per_value(fg):
    out = fg["guards"].fallback_alarms([25.0, 19.9, 130.0, 130.5, 20.0], 20.0, 130.0)
    assert out == [False, True, False, True, False]
    assert all(type(v) is bool for v in out)


def test_all_finite(fg):
    g = fg["guards"]
    assert g.all_finite([0.0, 1.5, 1e300]) is True
    for bad in ([1.0, math.nan], [math.inf], [-math.inf, 0.0], np.array([1.0, np.nan])):
        assert g.all_finite(bad) is False
    assert g.all_finite([]) is True
