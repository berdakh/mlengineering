"""Fixtures for the w7d5 lab checks. Grades <target>/src/flowguard/{guards,api,client}.py and <target>/tests.

All data is SYNTHETIC; no network (httpx.MockTransport and FastAPI's TestClient), no downloaded data.
"""
from __future__ import annotations

import importlib
import json
import logging
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w7d5_reliability"
BURN = [100.0, 101.0, 99.0, 100.5, 99.5, 100.2, 99.8, 100.1, 99.9, 100.0]


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def fg(target):
    src = target / "src"
    assert (src / "flowguard" / "api.py").is_file(), f"no {src}/flowguard/api.py"
    sys.path.insert(0, str(src))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    try:
        return {n: importlib.import_module(f"flowguard.{n}")
                for n in ("api", "guards", "client", "settings", "bundle", "scoring")}
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard from {src}: {exc!r}", pytrace=False)


@pytest.fixture()
def settings(fg):
    return fg["settings"].Settings(deadline_s=0.25, max_inflight=2, retry_after_s=2, support_low=0.0,
                                   support_high=200.0, envelope_low=20.0, envelope_high=130.0)


@pytest.fixture()
def bundle_dir(fg, tmp_path):
    model = fg["scoring"].ZScoreModel(sensor="flow_rate", n_burn_in=10, threshold=3.0, min_duration=1,
                                      merge_gap=0, model_version="synthetic-check-1")
    return fg["bundle"].save_bundle(model, tmp_path / "bundle")


@pytest.fixture()
def make_client(fg, bundle_dir, settings):
    from fastapi.testclient import TestClient
    clients = []

    def _make(faults=None, settings_=None, model_dir=None):
        app = fg["api"].create_app(model_dir or bundle_dir, settings=settings_ or settings, faults=faults or {})
        c = TestClient(app, raise_server_exceptions=False)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture()
def events(caplog):
    """Parsed JSON log events from the 'flowguard' logger."""
    caplog.set_level(logging.INFO, logger="flowguard")

    def _events():
        out = []
        for rec in caplog.records:
            if rec.name == "flowguard":
                try:
                    out.append(json.loads(rec.getMessage()))
                except json.JSONDecodeError:
                    pass
        return out
    return _events


def metric(text: str, line_prefix: str) -> float:
    """Value of the first /metrics line that starts with ``line_prefix`` (0 if absent)."""
    for line in text.splitlines():
        if line.startswith(line_prefix + " ") or line == line_prefix:
            return float(line.rsplit(" ", 1)[1])
    return 0.0
