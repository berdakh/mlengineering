"""Fixtures for the t1 checks. Data is SYNTHETIC.

The checks regenerate the reservation table WITH the generator's true no-show probability, which the
learner's file does not contain, and also build a second table from a different seed so that
hard-coded answers fail.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
UNIT = "lessons/w8d6_final_assessment/t1_transfer"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lessons" / "w8d6_final_assessment" / "data"))

from tools.wbcheck import resolve_target  # noqa: E402
from make_data import SEED, TT_LEAKY, simulate_tabletop  # noqa: E402

LEAKY = list(TT_LEAKY)


@pytest.fixture(scope="session")
def mod():
    path = resolve_target(UNIT) / "evaluate.py"
    assert path.is_file(), f"no evaluate.py at {path}"
    spec = importlib.util.spec_from_file_location("t1_evaluate", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return module


@pytest.fixture(scope="session")
def shipped():
    return simulate_tabletop(SEED, with_truth=True)


@pytest.fixture(scope="session")
def reseeded():
    return simulate_tabletop(5, with_truth=True)


def learner_view(table):
    return table.drop(columns=["p_true"]).copy()
