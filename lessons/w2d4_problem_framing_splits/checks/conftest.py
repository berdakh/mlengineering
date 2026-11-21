"""Fixtures for the w2d4 lab checks. All data here is SYNTHETIC and tiny; no download is needed."""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w2d4_problem_framing_splits"
SENSORS = ["accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate"]
RAW_NAMES = ["Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure",
             "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"]
DEFAULT_SIZES = {"valve1": 8, "valve2": 2, "other": 6}


def synth_tidy(sizes: dict[str, int] | None = None, rows: int = 12, seed: int = 0,
               with_normal: bool = True) -> pd.DataFrame:
    """SYNTHETIC tidy table in the flowguard schema: a few short 'experiments' per family."""
    sizes = DEFAULT_SIZES if sizes is None else sizes
    rng = np.random.default_rng(seed)
    frames = []
    plan = [(fam, str(i)) for fam, n in sizes.items() for i in range(n)]
    if with_normal:
        plan.append(("anomaly-free", "anomaly-free"))
    for fam, name in plan:
        df = pd.DataFrame(rng.normal(size=(rows, len(SENSORS))), columns=SENSORS)
        df.insert(0, "datetime", pd.date_range("2020-03-01", periods=rows, freq="s"))
        df.insert(0, "t", range(rows))
        df.insert(0, "family", fam)
        df.insert(0, "experiment_id", f"{fam}/{name}")
        df["anomaly"] = 0 if fam == "anomaly-free" else (np.arange(rows) >= rows // 2).astype(int)
        df["changepoint"] = 0
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def write_raw(tidy: pd.DataFrame, raw_dir: Path) -> Path:
    """Write a tidy frame back out in the raw SKAB file layout and format (semicolon separated)."""
    for exp, g in tidy.groupby("experiment_id"):
        fam, name = exp.split("/")
        out = g[["datetime", *SENSORS]].rename(columns=dict(zip(SENSORS, RAW_NAMES)))
        if fam != "anomaly-free":
            out = out.assign(anomaly=g["anomaly"].astype(float), changepoint=g["changepoint"].astype(float))
        (raw_dir / fam).mkdir(parents=True, exist_ok=True)
        out.to_csv(raw_dir / fam / f"{name}.csv", sep=";", index=False)
    return raw_dir


def labelled_ids(tidy: pd.DataFrame) -> set[str]:
    return set(tidy.loc[tidy["family"] != "anomaly-free", "experiment_id"])


def assigned_ids(manifest: dict) -> list[str]:
    return list(manifest["test"]) + [e for fold in manifest["dev_folds"] for e in fold]


@pytest.fixture(scope="session")
def target() -> Path:
    t = resolve_target(UNIT, "lab")
    assert (t / "src" / "flowguard").is_dir(), f"no package found at {t}/src/flowguard"
    return t


@pytest.fixture(scope="session")
def splits(target):
    sys.path.insert(0, str(target / "src"))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    return importlib.import_module("flowguard.splits")


@pytest.fixture()
def tidy() -> pd.DataFrame:
    return synth_tidy()


@pytest.fixture(scope="session")
def run_cli(target):
    env = dict(os.environ, PYTHONPATH=str(target / "src"), PYTHONDONTWRITEBYTECODE="1")
    entry = "import sys; from flowguard.cli import main; sys.exit(main())"

    def _run(*args, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-c", entry, *map(str, args)],
                              cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    return _run
