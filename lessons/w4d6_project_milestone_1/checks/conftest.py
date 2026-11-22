"""Fixtures for the w4d6 lab checks.

The checks copy YOUR lab (Makefile, src/) into a temporary project, add a tiny SYNTHETIC data set in
SKAB format and a split manifest (checks/synthetic.py), and run `make evaluate` there. Nothing is
written into your lab directory, and no downloaded data is needed.
"""
from __future__ import annotations

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

UNIT = "lessons/w4d6_project_milestone_1"
MAKE_VARS = ["BURN_IN=40", "N_BOOT=100", f"PY={sys.executable}"]
TIDY, RESULTS, REPORT = "data/interim/skab.csv", "results/results.json", "reports/evaluation.md"


def make(project: Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(["make", "--no-print-directory", "-C", str(project), *args, *MAKE_VARS],
                          capture_output=True, text=True, env=env, timeout=timeout)


def new_project(tmp: Path) -> Path:
    target = resolve_target(UNIT, "lab")
    for need in ("Makefile", "src"):
        assert (target / need).exists(), f"{target} has no {need}"
    project = tmp / "project"
    project.mkdir(parents=True, exist_ok=True)
    shutil.copy(target / "Makefile", project / "Makefile")
    shutil.copytree(target / "src", project / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    synthetic.write_project(project)
    return project


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    """A project after one successful `make evaluate`, plus the bytes of its outputs."""
    if shutil.which("make") is None:
        pytest.skip("GNU make is not installed (sudo apt install make)")
    project = new_project(tmp_path_factory.mktemp("w4d6"))
    proc = make(project, "evaluate")
    if proc.returncode != 0:
        pytest.fail(f"`make evaluate` failed (exit {proc.returncode}).\nstdout:\n{proc.stdout[-2500:]}\n"
                    f"stderr:\n{proc.stderr[-2500:]}", pytrace=False)
    return {"project": project, "report": (project / REPORT).read_bytes(),
            "results": (project / RESULTS).read_bytes()}
