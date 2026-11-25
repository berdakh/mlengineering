"""Fixtures for the w4d4 lab checks. Grades <target>/src/flowguard/tracking.py with the SYNTHETIC task."""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w4d4_experiment_tracking"
TARGET = resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def tr():
    assert (TARGET / "src" / "flowguard").is_dir(), f"no package found at {TARGET}/src/flowguard"
    sys.path.insert(0, str(TARGET / "src"))
    try:
        return importlib.import_module("flowguard.tracking")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.tracking from {TARGET}/src: {exc!r}", pytrace=False)


def spec(seeds=(0, 1, 2), alphas=(0.1, 10.0), noises=(1.0, 2.0), name="ridge", **base_data) -> dict:
    """A SYNTHETIC grid sweep: len(alphas) x len(noises) points x len(seeds) runs."""
    return {"sweep": {"name": name, "task": "synthetic", "mode": "grid", "seeds": list(seeds)},
            "base": {"data": {"n_rows": 120, **base_data}, "model": {}},
            "grid": {"model": {"alpha": list(alphas)}, "data": {"noise": list(noises)}}}


def spec_toml(path: Path, alphas=(0.1, 10.0), seeds=(0, 1, 2), name="ridge", extra_data: str = "") -> Path:
    path.write_text(f"""
[sweep]
name = "{name}"
task = "synthetic"
mode = "grid"
seeds = {list(seeds)}

[base.data]
n_rows = 120
{extra_data}

[grid.model]
alpha = {list(alphas)}
""")
    return path


def cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(TARGET / "src"), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "flowguard.cli", *args], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=120)
