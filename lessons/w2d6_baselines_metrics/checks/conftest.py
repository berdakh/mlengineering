"""Fixtures for the w2d6 lab checks. Grades <target>/src/flowguard. All data here is SYNTHETIC."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w2d6_baselines_metrics"


@pytest.fixture(scope="session")
def target() -> Path:
    t = resolve_target(UNIT, "lab")
    assert (t / "src" / "flowguard").is_dir(), f"no package found at {t}/src/flowguard"
    sys.path.insert(0, str(t / "src"))
    return t


def _load(target, name):
    try:
        return importlib.import_module(f"flowguard.{name}")
    except Exception as exc:  # noqa: BLE001 - report any import problem as a plain failure
        pytest.fail(f"could not import flowguard.{name} from {target}/src: {exc!r}", pytrace=False)


@pytest.fixture(scope="session")
def metrics(target):
    return _load(target, "metrics")


@pytest.fixture(scope="session")
def baselines(target):
    return _load(target, "baselines")


@pytest.fixture(scope="session")
def benchmark(target):
    return _load(target, "benchmark")
