"""Starter: one smoke test. Grow this directory into a suite that pins down lab/CONTRACT.md.

Run from the repository root:
    PYTHONPATH=labs/w5d5_api_testing/lab/service python -m pytest labs/w5d5_api_testing/lab/tests -q
"""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))   # harmless if absent

from flowguard.api import create_app  # noqa: E402
from flowguard.bundle import save_bundle  # noqa: E402
from flowguard.scoring import ZScoreModel  # noqa: E402


def test_healthz_answers(tmp_path):
    save_bundle(ZScoreModel("flow_rate", 100, 3.0, 30, 10, "smoke-1"), tmp_path / "bundle")
    with TestClient(create_app(tmp_path / "bundle")) as client:
        assert client.get("/healthz").status_code == 200
