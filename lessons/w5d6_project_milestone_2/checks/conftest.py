"""Fixtures for the w5d6 lab checks.

The checks copy YOUR lab (Makefile, src/, tests/, configs/, README.md, CHANGELOG.md, pyproject.toml)
into a temporary project, add a tiny SYNTHETIC data set in SKAB format with a matching split manifest
(checks/synthetic.py; it replaces splits/v2.json in the copy), and run make and the CLI there.
Nothing is written into your lab directory, and no downloaded data is needed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE)]

from tools.wbcheck import resolve_target  # noqa: E402

import synthetic  # noqa: E402

UNIT = "lessons/w5d6_project_milestone_2"
COPY = ("Makefile", "src", "tests", "configs", "README.md", "CHANGELOG.md", "pyproject.toml")


def env_for(project: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "WB_TARGET_DIR")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(project / "src"),
               RAW=str(project / "data" / "raw" / "skab"))
    return env


def make(project: Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    if shutil.which("make") is None:
        pytest.fail("GNU make is not installed (sudo apt install make)", pytrace=False)
    return subprocess.run(["make", "--no-print-directory", "-C", str(project), *args, f"PY={sys.executable}",
                           f"RAW={project / 'data' / 'raw' / 'skab'}"],
                          capture_output=True, text=True, env=env_for(project), timeout=timeout)


@pytest.fixture(scope="session")
def project(tmp_path_factory) -> Path:
    target = resolve_target(UNIT, "lab")
    root = tmp_path_factory.mktemp("project")
    for name in COPY:
        src = target / name
        assert src.exists(), f"{target} has no {name}"
        if src.is_dir():
            shutil.copytree(src, root / name, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        else:
            shutil.copy2(src, root / name)
    synthetic.write_project(root)          # data/raw/skab/... and splits/v2.json
    return root


@pytest.fixture(scope="session")
def built(project) -> subprocess.CompletedProcess:
    return make(project, "model")


@pytest.fixture(scope="session")
def probe(project, built) -> dict:
    assert built.returncode == 0, "make model failed:\n" + built.stdout[-1500:] + built.stderr[-1500:]
    proc = subprocess.run([sys.executable, str(HERE / "probe.py"), "models/current", "data/raw/skab"],
                          cwd=project, capture_output=True, text=True, env=env_for(project), timeout=300)
    assert proc.returncode == 0, "the parity probe could not run your package:\n" + proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])
