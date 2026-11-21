"""Fixtures for the w1d4 challenge checks (`pumpwatch compare-runs RUN_A RUN_B`)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w1d4_config_logging"
DATA = ROOT / "data" / "synthetic" / "pump_vibration.csv"
ENTRY = "import sys; from pumpwatch.cli import main; sys.exit(main())"


class Cli:
    def __init__(self, target: Path, workdir: Path):
        self.workdir = workdir
        self.env = dict(os.environ, PYTHONPATH=str(target / "src"), PYTHONDONTWRITEBYTECODE="1")

    def run(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-c", ENTRY, *map(str, args)], cwd=self.workdir,
                              env=self.env, capture_output=True, text=True, timeout=120)

    def train(self, name: str, data: Path, *extra: str) -> Path:
        config = self.workdir / f"{name}.toml"
        config.write_text(f'[data]\npath = "{data}"\n\n[split]\nseed = 7\n\n[model]\nC = 1.0\n')
        parent = self.workdir / f"runs_{name}"
        proc = self.run("train", "--config", config, "--run-dir", parent, *extra)
        assert proc.returncode == 0, proc.stderr[-1500:]
        (run_dir,) = [p for p in parent.iterdir() if p.is_dir()]
        return run_dir

    def compare(self, a: Path, b: Path) -> dict:
        proc = self.run("compare-runs", a, b)
        assert proc.returncode == 0, f"compare-runs failed:\n{proc.stderr[-1500:]}"
        return json.loads(proc.stdout)


@pytest.fixture(scope="session")
def cli(tmp_path_factory) -> Cli:
    target = resolve_target(UNIT, "challenge")
    assert (target / "src" / "pumpwatch").is_dir(), (
        f"no package at {target}/src/pumpwatch - copy your finished lab package into challenge/ first")
    return Cli(target, tmp_path_factory.mktemp("w1d4_challenge"))


@pytest.fixture(scope="session")
def runs(cli) -> dict[str, Path]:
    """base / tuned (seed and C changed) / copy (same bytes, other path) / edited (same path, other bytes)."""
    work = cli.workdir
    copied = work / "copy_of_data.csv"
    shutil.copyfile(DATA, copied)
    mutable = work / "mutable.csv"
    shutil.copyfile(DATA, mutable)
    out = {
        "base": cli.train("base", DATA),
        "tuned": cli.train("tuned", DATA, "--set", "split.seed=3", "--set", "model.C=0.1"),
        "copy": cli.train("copy", copied),
        "before_edit": cli.train("before_edit", mutable),
    }
    df = pd.read_csv(mutable)
    df[~((df.unit_id == "P10") & (df.window_id >= 25))].to_csv(mutable, index=False)
    out["after_edit"] = cli.train("after_edit", mutable)
    return out
