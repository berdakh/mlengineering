"""Fixtures for the w1d3 challenge checks. Grades challenge/ unless WB_TARGET_DIR is set."""
from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w1d3_package_structure"
PART = "challenge"
DATA = ROOT / "data" / "synthetic" / "pump_vibration.csv"


@pytest.fixture(scope="session")
def data_csv() -> Path:
    if not DATA.is_file():
        pytest.fail(f"{DATA} is missing - run: python data/make_pump_data.py")
    return DATA


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, PART)


@pytest.fixture(scope="session")
def pyproject(target) -> dict:
    path = target / "pyproject.toml"
    if not path.is_file():
        pytest.fail(f"no pyproject.toml in {target} - the package root must be the {PART}/ directory")
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        pytest.fail(f"pyproject.toml is not valid TOML: {exc}")


@pytest.fixture(scope="session")
def src(target) -> Path:
    path = target / "src"
    if not (path / "pumpwatch" / "__init__.py").is_file():
        pytest.fail(f"expected an import package at {path / 'pumpwatch'} (src layout)")
    return path


@pytest.fixture(scope="session")
def entry_point(pyproject) -> tuple[str, str]:
    spec = pyproject.get("project", {}).get("scripts", {}).get("pumpwatch")
    if not spec or ":" not in spec:
        pytest.fail("[project.scripts] must define  pumpwatch = \"<module>:<callable>\"")
    module, func = spec.split(":", 1)
    return module.strip(), func.strip()


@pytest.fixture(scope="session")
def run_cli(src, entry_point):
    """Run the CLI from a chosen working directory with the source tree on PYTHONPATH.
    how="script" mimics the generated console script; how="module" runs `python -m pumpwatch`."""
    module, func = entry_point
    launcher = f"import sys; from {module} import {func} as _f; sys.exit(_f())"

    def _run(args: list, cwd: Path, how: str = "script") -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONPATH=str(src), PYTHONDONTWRITEBYTECODE="1")
        head = ["-c", launcher] if how == "script" else ["-m", "pumpwatch"]
        return subprocess.run(
            [sys.executable, *head, *map(str, args)],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=180,
        )

    return _run
