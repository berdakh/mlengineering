"""Fixtures for the w7d6 lab checks.

The checks copy YOUR lab (src/, configs/, RUNBOOK.md, ...) to a temporary directory, write a tiny
SYNTHETIC data set, manifest and scenario (checks/synthetic.py), and run
`python -m flowguard monitor-demo` there twice. Nothing is written into your lab directory; no downloaded
data is needed. Each run starts real uvicorn processes on 127.0.0.1 and must stop them.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE)]

from tools.wbcheck import resolve_target  # noqa: E402

import synthetic  # noqa: E402

UNIT = "labs/w7d6_project_milestone_4"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def project(target, tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("project")
    for name in ("src", "configs"):
        assert (target / name).is_dir(), f"{target} has no {name}/"
        shutil.copytree(target / name, root / name, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    root.joinpath("data").mkdir()
    return root


@pytest.fixture(scope="session")
def data(project) -> dict:
    return synthetic.write(project / "data")


def run_demo(project: Path, data: dict, out: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "WB_TARGET_DIR", "FLOWGUARD_FAULTS")}
    env.update(PYTHONPATH=str(project / "src"), PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg")
    return subprocess.run([sys.executable, "-m", "flowguard", "monitor-demo", "--raw", str(data["raw"]),
                           "--splits", str(data["splits"]), "--scenario", str(data["scenario"]), "--out", out],
                          cwd=project, env=env, capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="session")
def runs(project, data):
    out = []
    for name in ("run1", "run2"):
        proc = run_demo(project, data, name)
        res_path = project / name / "results.json"
        out.append({"proc": proc, "dir": project / name,
                    "results": json.loads(res_path.read_text()) if res_path.is_file() else None,
                    "report": (project / name / "monitoring_demo.md").read_text()
                    if (project / name / "monitoring_demo.md").is_file() else None})
    yield out
    # Teardown: never leave a leaked service behind, whatever the checks concluded.
    for r in out:
        for pid in (r["results"] or {}).get("server", {}).get("pids", []):
            try:
                os.kill(pid, 15)
            except OSError:
                pass


@pytest.fixture(scope="session")
def first(runs) -> dict:
    r = runs[0]
    assert r["results"] is not None and r["report"] is not None, (
        "monitor-demo did not write results.json and monitoring_demo.md:\n"
        + r["proc"].stdout[-1500:] + r["proc"].stderr[-2500:])
    return r


@pytest.fixture(scope="session")
def scenario() -> dict:
    return tomllib.loads(synthetic.SCENARIO)


@pytest.fixture(scope="session")
def alerts(target) -> list[dict]:
    path = target / "configs" / "alerts.toml"
    assert path.is_file(), "configs/alerts.toml is missing"
    return tomllib.loads(path.read_text())["alert"]
