"""Fixtures for the w1d6 checks. Grades lab/ unless WB_TARGET_DIR is set.

The project for this unit is meant to live in its own Git repository outside the
course repository, so the usual invocation is

    WB_TARGET_DIR=~/projects/flowguard python -m pytest labs/w1d6_notebook_to_package/checks -q

All data used here is SYNTHETIC: tiny files in the SKAB raw format written to a
temporary directory. No download is needed.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w1d6_notebook_to_package"
PART = "lab"
PACKAGE = "flowguard"

RAW_SENSORS = ["Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure",
               "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"]
CANONICAL_SENSORS = ["accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
                     "temperature", "thermocouple", "voltage", "flow_rate"]
TIDY_COLUMNS = ["experiment_id", "family", "t", "datetime", *CANONICAL_SENSORS, "anomaly", "changepoint"]

# experiment_id -> (rows, start, labelled, shuffled rows on disk)
SPEC = {
    "valve1/0": (20, "2020-03-09 10:00:00", True, False),
    "valve1/1": (21, "2020-03-09 10:30:00", True, False),
    "valve1/2": (22, "2020-03-09 11:00:00", True, True),
    "valve1/10": (30, "2020-03-09 12:00:00", True, False),
    "other/1": (12, "2020-03-01 15:00:00", True, False),
    "other/3": (13, "2020-03-01 15:00:05", True, False),   # overlaps other/1 in wall-clock time
    "anomaly-free/anomaly-free": (40, "2020-02-08 13:00:00", False, False),
}


def make_raw_frame(n_rows: int, start: str, labelled: bool, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"datetime": pd.date_range(start, periods=n_rows, freq="s").strftime("%Y-%m-%d %H:%M:%S")})
    for i, name in enumerate(RAW_SENSORS):
        df[name] = np.round(rng.normal(10.0 * (i + 1), 1.0, n_rows), 4)   # sensor i is centred on 10*(i+1)
    if labelled:
        anomaly = np.zeros(n_rows)
        anomaly[n_rows // 2:] = 1.0
        df["anomaly"] = anomaly
        df["changepoint"] = 0.0
        df.loc[n_rows // 2, "changepoint"] = 1.0
    return df


def write_raw(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=";", index=False)


@pytest.fixture(scope="session")
def raw_dir(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("synthetic_skab")
    for seed, (experiment_id, (n, start, labelled, shuffled)) in enumerate(SPEC.items()):
        df = make_raw_frame(n, start, labelled, seed)
        if shuffled:
            df = df.sample(frac=1.0, random_state=0)
        write_raw(root / f"{experiment_id}.csv", df)
    (root / "MANIFEST.json").write_text("{}")
    return root


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, PART)


@pytest.fixture(scope="session")
def pyproject(target) -> dict:
    path = target / "pyproject.toml"
    if not path.is_file():
        pytest.fail(f"no pyproject.toml in {target}. If your project lives elsewhere, set WB_TARGET_DIR to it.")
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        pytest.fail(f"pyproject.toml is not valid TOML: {exc}")


@pytest.fixture(scope="session")
def src(target, pyproject) -> Path:
    path = target / "src"
    if not (path / PACKAGE / "__init__.py").is_file():
        pytest.fail(f"expected an import package at {path / PACKAGE} (src layout)")
    return path


@pytest.fixture(scope="session")
def entry_point(pyproject) -> tuple[str, str]:
    spec = pyproject.get("project", {}).get("scripts", {}).get(PACKAGE)
    if not spec or ":" not in spec:
        pytest.fail(f'[project.scripts] must define  {PACKAGE} = "<module>:<callable>"')
    module, func = spec.split(":", 1)
    return module.strip(), func.strip()


@pytest.fixture(scope="session")
def run_cli(src, entry_point):
    """Run the console entry point as the generated script would, from a chosen cwd."""
    module, func = entry_point
    launcher = f"import sys; from {module} import {func} as _f; sys.exit(_f())"

    def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONPATH=str(src), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-c", launcher, *map(str, args)],
                              cwd=cwd, env=env, capture_output=True, text=True, timeout=120)

    return _run


@pytest.fixture(scope="session")
def data_module(src):
    for name in [m for m in sys.modules if m == PACKAGE or m.startswith(PACKAGE + ".")]:
        del sys.modules[name]
    sys.path.insert(0, str(src))
    try:
        return importlib.import_module(f"{PACKAGE}.data")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {PACKAGE}.data from {src}: {exc!r}")


@pytest.fixture(scope="session")
def tidy(data_module, raw_dir) -> pd.DataFrame:
    return data_module.load_raw(raw_dir)
