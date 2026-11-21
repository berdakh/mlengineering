"""Shared fixtures for the w1d4 lab checks. Grades <target>/src/pumpwatch via its CLI contract."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w1d4_config_logging"
DATA = ROOT / "data" / "synthetic" / "pump_vibration.csv"
ENTRY = "import sys; from pumpwatch.cli import main; sys.exit(main())"


class Cli:
    """Runs the target's CLI in a subprocess and collects run directories."""

    def __init__(self, target: Path):
        self.target = target
        self.env = dict(os.environ, PYTHONPATH=str(target / "src"), PYTHONDONTWRITEBYTECODE="1")

    def run(self, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-c", ENTRY, *map(str, args)],
                              cwd=cwd, env=self.env, capture_output=True, text=True, timeout=120)

    def train(self, workdir: Path, config: Path, *extra: str) -> "Run":
        """Train into a fresh parent directory so the new run folder is unambiguous."""
        parent = workdir / f"runs_{len(list(workdir.glob('runs_*')))}"
        proc = self.run("train", "--config", config, "--run-dir", parent, *extra, cwd=workdir)
        return Run(proc, parent)


class Run:
    def __init__(self, proc: subprocess.CompletedProcess, parent: Path):
        self.proc, self.parent = proc, parent

    @property
    def dir(self) -> Path:
        assert self.proc.returncode == 0, f"train failed (exit {self.proc.returncode}):\n{self.proc.stderr[-1500:]}"
        dirs = [p for p in self.parent.iterdir() if p.is_dir()] if self.parent.is_dir() else []
        assert len(dirs) == 1, f"expected exactly one run directory inside --run-dir, found {len(dirs)}"
        return dirs[0]

    def json(self, name: str) -> dict:
        path = self.dir / name
        assert path.is_file(), f"run directory is missing {name}"
        return json.loads(path.read_text())


def write_config(path: Path, body: str | None = None) -> Path:
    if body is None:
        body = f'[data]\npath = "{DATA}"\nfs = 256.0\n\n[split]\ntest_fraction = 0.3\nseed = 7\n\n' \
               '[model]\nC = 1.0\n\n[logging]\nlevel = "INFO"\n'
    path.write_text(body)
    return path


@pytest.fixture(scope="session")
def target() -> Path:
    t = resolve_target(UNIT, "lab")
    assert (t / "src" / "pumpwatch").is_dir(), f"no package found at {t}/src/pumpwatch"
    return t


@pytest.fixture(scope="session")
def cli(target) -> Cli:
    return Cli(target)


@pytest.fixture(scope="session")
def workdir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("w1d4")


@pytest.fixture(scope="session")
def base_config(workdir) -> Path:
    return write_config(workdir / "base.toml")


@pytest.fixture(scope="session")
def base_run(cli, workdir, base_config) -> Run:
    """One ordinary successful run, shared by the read-only checks."""
    return cli.train(workdir, base_config)
