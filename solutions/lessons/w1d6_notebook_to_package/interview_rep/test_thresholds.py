"""Run:  python -m pytest solutions/lessons/w1d6_notebook_to_package/interview_rep -q

The same four tests run against the buggy and the fixed module. Against the buggy
module two of them fail, and which two depends on nothing but call order inside
each test - that is the point of the exercise.
"""
import importlib
import json

import pytest


@pytest.fixture(params=["thresholds_buggy", "thresholds_fixed"])
def load_thresholds(request, monkeypatch):
    monkeypatch.syspath_prepend(str(request.path.parent))
    module = importlib.import_module(request.param)
    module._CACHE.clear()
    if request.param == "thresholds_buggy":
        request.applymarker(pytest.mark.xfail(strict=False, reason="demonstrates the defect"))
    return module.load_thresholds


@pytest.fixture
def path(tmp_path):
    p = tmp_path / "thresholds.json"
    p.write_text(json.dumps({"pressure": 2.0, "current": 5.0}))
    return str(p)


def test_defaults(load_thresholds, path):
    assert load_thresholds(path) == {"pressure": 2.0, "current": 5.0}


def test_override_applies(load_thresholds, path):
    assert load_thresholds(path, {"pressure": 1.5})["pressure"] == 1.5


def test_override_does_not_leak_into_later_calls(load_thresholds, path):
    load_thresholds(path, {"pressure": 1.5})
    assert load_thresholds(path)["pressure"] == 2.0


def test_caller_cannot_corrupt_the_cache(load_thresholds, path):
    load_thresholds(path)["current"] = -1.0
    assert load_thresholds(path)["current"] == 5.0
