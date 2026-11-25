"""Fixtures for the w8d2 lab checks.

Your checker (lab/report/check_report.py) is run as a subprocess on SYNTHETIC reports
(checks/synthetic_reports.py): one that follows every rule and six that each break exactly one.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE)]

from tools.wbcheck import resolve_target  # noqa: E402

import synthetic_reports  # noqa: E402

UNIT = "lessons/w8d2_report_limitations"


@pytest.fixture(scope="session")
def tool() -> Path:
    path = resolve_target(UNIT, "lab") / "report" / "check_report.py"
    assert path.is_file(), f"missing {path}"
    return path


@pytest.fixture(scope="session")
def results_file(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("results") / "results.json"
    path.write_text(json.dumps(synthetic_reports.RESULTS))
    return path


def run(tool: Path, report_text: str, results_file: Path, tmp: Path, *extra: str) -> dict:
    report = tmp / "REPORT.md"
    report.write_text(report_text)
    out = tmp / "findings.json"
    proc = subprocess.run([sys.executable, str(tool), str(report), "--results", str(results_file),
                           "--json", str(out), *extra], capture_output=True, text=True, timeout=60)
    data = json.loads(out.read_text()) if out.is_file() else None
    assert data is not None, f"no --json output written:\n{proc.stdout[-800:]}{proc.stderr[-1500:]}"
    return {"proc": proc, "data": data, "codes": {f["code"] for f in data["findings"]}}


@pytest.fixture(scope="session")
def good(tool, results_file, tmp_path_factory) -> dict:
    return run(tool, synthetic_reports.good_report(), results_file, tmp_path_factory.mktemp("good"))


@pytest.fixture(scope="session")
def bad(tool, results_file, tmp_path_factory) -> dict:
    return {name: (run(tool, text, results_file, tmp_path_factory.mktemp(name)), code)
            for name, (text, code) in synthetic_reports.variants().items()}
