"""Fixtures for the w3d6 challenge checks (transfer exercise part 2). Data is SYNTHETIC.

The checks regenerate the invoice table WITH the generator's true late-probability, which the
learner's file does not contain, and also build a second table from a different seed so that
hard-coded answers fail.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UNIT = "lessons/w3d6_error_analysis_transfer"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / UNIT / "data"))

from tools.wbcheck import resolve_target  # noqa: E402
from make_invoices import SEED, simulate  # noqa: E402

LEAKY = ["days_to_payment", "reminders_sent", "customer_late_rate", "account_status"]


@pytest.fixture(scope="session")
def mod():
    path = resolve_target(UNIT, "challenge") / "evaluate.py"
    assert path.is_file(), f"no evaluate.py at {path}"
    spec = importlib.util.spec_from_file_location("w3d6_evaluate", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return module


@pytest.fixture(scope="session")
def shipped():
    return simulate(SEED, with_truth=True)


@pytest.fixture(scope="session")
def reseeded():
    return simulate(5, with_truth=True)


def learner_view(table):
    return table.drop(columns=["p_true"]).copy()
