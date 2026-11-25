"""Fixtures for the w2d5 lab checks. Grades <target>/src/flowguard. Offline; SYNTHETIC frames only."""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from tools.wbcheck import resolve_target  # noqa: E402

import synth  # noqa: E402

UNIT = "labs/w2d5_feature_pipeline"
WINDOWS = (5, 12)
COLUMNS = ("current", "pressure", "flow_rate")
ENTRY = "import sys; from flowguard.cli import main; sys.exit(main())"


@pytest.fixture(scope="session")
def target() -> Path:
    t = resolve_target(UNIT, "lab")
    assert (t / "src" / "flowguard").is_dir(), f"no package found at {t}/src/flowguard"
    return t


@pytest.fixture(scope="session")
def features_module(target):
    sys.path.insert(0, str(target / "src"))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    return importlib.import_module("flowguard.features")


@pytest.fixture()
def tidy():
    return synth.make_tidy()


@pytest.fixture(scope="session")
def build(features_module):
    """Call the learner's function with the small windows used throughout the checks."""
    def _build(frame, windows=WINDOWS, columns=COLUMNS, max_gap_s=5.0):
        try:
            return features_module.causal_rolling_features(frame, windows=windows, columns=columns,
                                                           max_gap_s=max_gap_s)
        except NotImplementedError:
            pytest.fail("causal_rolling_features is not implemented yet", pytrace=False)
    return _build


@pytest.fixture(scope="session")
def run_cli(target):
    env = dict(os.environ, PYTHONPATH=str(target / "src"), PYTHONDONTWRITEBYTECODE="1")

    def _run(*args, cwd):
        return subprocess.run([sys.executable, "-c", ENTRY, *map(str, args)], cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=120)
    return _run
