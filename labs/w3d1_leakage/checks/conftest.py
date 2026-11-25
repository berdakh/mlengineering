"""Fixtures for the w3d1 lab checks. All data built here is SYNTHETIC and tiny; no download is needed."""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w3d1_leakage"
SENSORS = ["accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate"]
DEFAULT_SIZES = {"valve1": 8, "valve2": 3, "other": 7}


def synth_tidy(sizes: dict[str, int] | None = None, rows: int = 40, seed: int = 0,
               onset: str = "half") -> pd.DataFrame:
    """SYNTHETIC tidy table in the flowguard schema. Every experiment gets its own time range.

    onset="half":   the anomaly starts at the midpoint of every experiment (the clock predicts it);
    onset="random": each experiment is anomalous in a random contiguous block that may come first.
    """
    sizes = DEFAULT_SIZES if sizes is None else sizes
    rng = np.random.default_rng(seed)
    frames = []
    plan = [(fam, str(i)) for fam, n in sizes.items() for i in range(n)] + [("anomaly-free", "anomaly-free")]
    for k, (fam, name) in enumerate(plan):
        df = pd.DataFrame(rng.normal(size=(rows, len(SENSORS))).round(6), columns=SENSORS)
        df.insert(0, "datetime", pd.date_range("2020-03-01", periods=rows, freq="s") + pd.Timedelta(days=k))
        df.insert(0, "t", range(rows))
        df.insert(0, "family", fam)
        df.insert(0, "experiment_id", f"{fam}/{name}")
        if fam == "anomaly-free":
            label = np.zeros(rows, dtype=int)
        elif onset == "half":
            label = (np.arange(rows) >= rows // 2).astype(int)
        else:
            start = int(rng.integers(0, rows // 2 + 1))
            label = ((np.arange(rows) >= start) & (np.arange(rows) < start + rows // 2)).astype(int)
        df["anomaly"] = label
        df["changepoint"] = 0
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def plant_overlap(tidy: pd.DataFrame, source: str, dest: str, n: int = 5, flip_labels: bool = False,
                  src_offset: int = 0, dest_offset: int = 0) -> pd.DataFrame:
    """Copy ``n`` rows (timestamp + sensors) of ``source`` into ``dest``, as two SKAB files share rows."""
    tidy = tidy.copy()
    src = tidy.index[tidy["experiment_id"] == source][src_offset:src_offset + n]
    dst = tidy.index[tidy["experiment_id"] == dest][dest_offset:dest_offset + n]
    cols = ["datetime", *SENSORS]
    tidy.loc[dst, cols] = tidy.loc[src, cols].to_numpy()
    if flip_labels:
        tidy.loc[dst, "anomaly"] = 1 - tidy.loc[src, "anomaly"].to_numpy()
    return tidy


def side_of(manifest: dict) -> dict[str, str]:
    side = {e: "test" for e in manifest["test"]}
    for i, fold in enumerate(manifest["dev_folds"]):
        side.update({e: f"fold{i}" for e in fold})
    return side


def as_sets(groups) -> list[frozenset]:
    return sorted((frozenset(g) for g in groups), key=lambda g: min(g))


def _fresh_import(target: Path, name: str):
    src = str(target / "src")
    if src in sys.path:
        sys.path.remove(src)
    sys.path.insert(0, src)
    for mod in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[mod]
    return importlib.import_module(name)


@pytest.fixture(scope="session")
def target() -> Path:
    t = resolve_target(UNIT, "lab")
    assert (t / "src" / "flowguard").is_dir(), f"no package found at {t}/src/flowguard"
    return t


@pytest.fixture(scope="session")
def splits(target):
    return _fresh_import(target, "flowguard.splits")


@pytest.fixture(scope="session")
def leakcheck(target, splits):
    return importlib.import_module("flowguard.leakcheck")


@pytest.fixture(scope="session")
def honest(target):
    path = target / "leakhunt" / "honest_eval.py"
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location("w3d1_honest_eval", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def generator():
    path = ROOT / UNIT / "data" / "make_invoices.py"
    spec = importlib.util.spec_from_file_location("w3d1_make_invoices", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def tidy() -> pd.DataFrame:
    return synth_tidy()
