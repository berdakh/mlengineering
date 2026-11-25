"""Fixtures for the w2d3 lab checks. Grades <target>/src/flowguard. Offline; SYNTHETIC inputs only."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.wbcheck import resolve_target  # noqa: E402

import synth  # noqa: E402

UNIT = "labs/w2d3_data_quality_ingestion"
TARGET = resolve_target(UNIT, "lab")
sys.path.insert(0, str(TARGET / "src"))
ENTRY = "import sys; from flowguard.cli import main; sys.exit(main())"


@pytest.fixture(scope="session")
def target() -> Path:
    assert (TARGET / "src" / "flowguard").is_dir(), f"no src/flowguard package in {TARGET}"
    return TARGET


@pytest.fixture()
def raw_dir(tmp_path):
    """Factory: raw_dir() is a clean synthetic raw directory, raw_dir('gap_300s') has one defect."""
    def make(defect: str | None = None, name: str | None = None) -> Path:
        frames = synth.clean_frames() if defect is None else synth.frames_with(defect)
        return synth.write_raw(tmp_path / (name or f"raw_{defect or 'clean'}"), frames)
    return make


@pytest.fixture()
def ingest_cli(target, tmp_path):
    def run(raw: Path, out: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONPATH=str(target / "src"), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-c", ENTRY, "ingest", "--raw-dir", str(raw), "--out-dir", str(out)],
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    return run


def failed(results):
    return [r for r in results if not r.passed]
