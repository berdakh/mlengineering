"""Fixtures for the w3d1 challenge checks. Data is SYNTHETIC, generated here from challenge/make_leads.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w3d1_leakage"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def leads():
    return _load(ROOT / UNIT / "challenge" / "make_leads.py", "w3d1_make_leads")


@pytest.fixture(scope="session")
def analysis():
    target = resolve_target(UNIT, "challenge")
    path = target / "honest_analysis.py"
    assert path.is_file(), f"missing {path}"
    return _load(path, "w3d1_honest_analysis")


@pytest.fixture(scope="session")
def noise_results(leads, analysis):
    """Pure-noise worlds: features carry no information about the label."""
    out = []
    for seed in (101, 102, 103, 104):
        X, y = leads.simulate(seed, n_signal=0)
        out.append(analysis.honest_estimate(X, y))
    return out


@pytest.fixture(scope="session")
def signal_results(leads, analysis):
    out = []
    for seed in (201, 202, 203):
        X, y = leads.simulate(seed, n_signal=6)
        X_new, y_new = leads.draw_more(seed, 20000, n_signal=6)
        out.append((analysis.honest_estimate(X, y), X_new, y_new))
    return out
