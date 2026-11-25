"""Fixtures for the w5d4 challenge checks: streaming endpoints. SYNTHETIC data, in-process TestClient."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w5d4_fastapi_validation"


@pytest.fixture(scope="session")
def fg():
    target = resolve_target(UNIT, "challenge")
    src = target / "src"
    assert (src / "flowguard" / "api.py").is_file(), \
        f"no {src}/flowguard/api.py: copy your finished lab/ into challenge/ first (see challenge/README.md)"
    sys.path.insert(0, str(src))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    try:
        return {n: importlib.import_module(f"flowguard.{n}") for n in ("api", "bundle", "inference")}
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard from {src}: {exc!r}", pytrace=False)


@pytest.fixture()
def model_dir(fg, tmp_path):
    det = fg["inference"].Detector(n_burn=20, threshold=3.0, version="synthetic-api-1")
    return fg["bundle"].save_bundle(det, tmp_path / "model")


@pytest.fixture()
def client(fg, model_dir):
    from fastapi.testclient import TestClient
    with TestClient(fg["api"].create_app(model_dir), raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def client_without_model(fg, tmp_path):
    from fastapi.testclient import TestClient
    with TestClient(fg["api"].create_app(tmp_path / "missing"), raise_server_exceptions=False) as c:
        yield c
