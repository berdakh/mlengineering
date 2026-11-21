"""Fixtures for the w1d3 lab checks. Grades lab/ unless WB_TARGET_DIR is set."""
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

UNIT = "lessons/w1d3_package_structure"
PART = "lab"
DATA = ROOT / "data" / "synthetic" / "pump_vibration.csv"


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: real install into a fresh venv (set WB_RUN_SLOW=1)")


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
    """Run the console entry point exactly as the generated script would:
    import the callable and pass its return value to sys.exit(). The source tree
    is put on PYTHONPATH so no installation is needed, and the working directory
    is chosen by the test (never the repository root)."""
    module, func = entry_point
    launcher = f"import sys; from {module} import {func} as _f; sys.exit(_f())"

    def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONPATH=str(src), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-c", launcher, *map(str, args)],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=180,
        )

    return _run


@pytest.fixture(scope="session")
def pkg(src):
    """Import the learner's package from <target>/src (not from any installed copy)."""
    for name in [m for m in sys.modules if m == "pumpwatch" or m.startswith("pumpwatch.")]:
        del sys.modules[name]
    sys.path.insert(0, str(src))
    import importlib

    try:
        modules = {n: importlib.import_module(f"pumpwatch.{n}") for n in ("io", "features", "split", "model")}
    except Exception as exc:  # noqa: BLE001 - report any import problem as a check failure
        pytest.fail(f"could not import the package from {src}: {exc!r}")
    return modules
