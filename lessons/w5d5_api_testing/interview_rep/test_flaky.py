"""Interview rep (debugging): this suite is "flaky". Explain why, then fix it.

    PYTHONPATH=lessons/w5d5_api_testing/lab/service python -m pytest lessons/w5d5_api_testing/interview_rep/test_flaky.py -q
    PYTHONPATH=lessons/w5d5_api_testing/lab/service python -m pytest lessons/w5d5_api_testing/interview_rep/test_flaky.py -q -k scores
"""
import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from flowguard.api import create_app
from flowguard.bundle import save_bundle
from flowguard.scoring import ZScoreModel

BUNDLE = Path(tempfile.mkdtemp()) / "bundle"
save_bundle(ZScoreModel("flow_rate", 100, 3.0, 30, 10, "flaky-1"), BUNDLE)


def test_tampered_bundle_is_not_ready():
    params = json.loads((BUNDLE / "model.json").read_text())
    params["threshold"] = 0.5
    (BUNDLE / "model.json").write_text(json.dumps(params))
    with TestClient(create_app(BUNDLE)) as client:
        assert client.get("/readyz").status_code == 503


def test_scores():
    with TestClient(create_app(BUNDLE)) as client:
        r = client.post("/predict", json={"burn_in": [-1.0, 1.0], "values": [2.0]})
        assert r.status_code == 200
        assert r.json()["scores"] == [2.0]
