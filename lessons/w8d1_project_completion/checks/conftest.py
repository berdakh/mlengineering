"""Fixtures for the w8d1 lab checks.

Your audit tool (lab/audit/clean_clone_check.py) is run as a subprocess against SYNTHETIC git
repositories built in a temporary directory (checks/synthetic_repo.py): one reproducible project and
six that each carry one defect. Nothing is downloaded; the synthetic project uses the standard library
only, so creating its virtual environment needs no network.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE)]

from tools.wbcheck import resolve_target  # noqa: E402

import synthetic_repo  # noqa: E402

UNIT = "lessons/w8d1_project_completion"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def tool(target) -> Path:
    path = target / "audit" / "clean_clone_check.py"
    assert path.is_file(), f"missing {path}"
    return path


@pytest.fixture(scope="session")
def repos(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("repos")
    return {v: synthetic_repo.make_repo(root, v) for v in synthetic_repo.VARIANTS}


def run_audit(tool: Path, repo: Path, log: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "WB_TARGET_DIR")}
    proc = subprocess.run([sys.executable, str(tool), str(repo), "--log", str(log)],
                          capture_output=True, text=True, env=env, timeout=300, cwd=log.parent)
    record_path = log.with_suffix(".json")
    record = json.loads(record_path.read_text()) if record_path.is_file() else None
    return {"proc": proc, "record": record, "log": log.read_text() if log.is_file() else None}


@pytest.fixture(scope="session")
def audits(tool, repos, tmp_path_factory) -> dict[str, dict]:
    out = {}
    for variant, repo in repos.items():
        logdir = tmp_path_factory.mktemp(f"log_{variant}")
        out[variant] = run_audit(tool, repo, logdir / "REPRODUCTION_LOG.md")
    return out


def codes(result: dict) -> set[str]:
    assert result["record"] is not None, (
        "the tool wrote no JSON record next to the log:\n" + result["proc"].stdout[-1000:] + result["proc"].stderr[-2000:])
    return {f["code"] for f in result["record"]["findings"]}
