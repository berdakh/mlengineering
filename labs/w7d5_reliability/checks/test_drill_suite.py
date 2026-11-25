"""Lab task 4: YOUR tests/ must pass on your service and catch broken services (failure-injection drills).

Each broken service in checks/broken/ replaces your src/flowguard/api.py in a temporary copy. A suite that
only checks the happy path lets all of them through.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BROKEN = sorted((HERE / "broken").glob("*.py"))


def run_suite(target: Path, tmp: Path, api_file: Path | None) -> subprocess.CompletedProcess:
    work = tmp / "lab"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(target / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(target / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    if api_file is not None:
        shutil.copy2(api_file, work / "src" / "flowguard" / "api.py")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "WB_TARGET_DIR", "FLOWGUARD_FAULTS")}
    env.update(PYTHONPATH=str(work / "src"), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-x", "-p", "no:cacheprovider"],
                          cwd=work, env=env, capture_output=True, text=True, timeout=180)


def test_suite_exists(target):
    assert (target / "tests").is_dir() and list((target / "tests").glob("test_*.py")), "no tests/test_*.py"


def test_suite_passes_on_your_service(target, tmp_path):
    proc = run_suite(target, tmp_path, None)
    assert proc.returncode == 0, "your tests fail on your own service:\n" + proc.stdout[-2000:]


@pytest.mark.parametrize("broken", BROKEN, ids=[p.stem for p in BROKEN])
def test_suite_catches_broken_service(target, tmp_path, broken):
    proc = run_suite(target, tmp_path, broken)
    assert proc.returncode != 0, (f"your tests pass against the broken service '{broken.stem}'. "
                                  f"See the first line of checks/broken/{broken.name} for what is wrong with it.")
