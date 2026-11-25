"""Fixed version of labs/w5d5_api_testing/interview_rep/test_flaky.py: every test owns its bundle."""
import json

import pytest
from fastapi.testclient import TestClient

from flowguard.api import create_app
from flowguard.bundle import save_bundle
from flowguard.scoring import ZScoreModel


@pytest.fixture
def bundle(tmp_path):
    return save_bundle(ZScoreModel("flow_rate", 100, 3.0, 30, 10, "flaky-1"), tmp_path / "bundle")


def test_tampered_bundle_is_not_ready(bundle):
    params = json.loads((bundle / "model.json").read_text())
    params["threshold"] = 0.5
    (bundle / "model.json").write_text(json.dumps(params))
    with TestClient(create_app(bundle)) as client:
        assert client.get("/readyz").status_code == 503


def test_scores(bundle):
    with TestClient(create_app(bundle)) as client:
        r = client.post("/predict", json={"burn_in": [-1.0, 1.0], "values": [2.0]})
        assert r.status_code == 200
        assert r.json()["scores"] == [2.0]
