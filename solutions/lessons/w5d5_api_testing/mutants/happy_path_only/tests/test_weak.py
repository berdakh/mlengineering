import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))

from flowguard.api import create_app  # noqa: E402
from flowguard.bundle import save_bundle  # noqa: E402
from flowguard.scoring import ZScoreModel  # noqa: E402


def test_predict_works(tmp_path):
    save_bundle(ZScoreModel("flow_rate", 100, 3.0, 30, 10, "v1"), tmp_path / "b")
    with TestClient(create_app(tmp_path / "b")) as client:
        assert client.get("/healthz").status_code == 200
        r = client.post("/predict", json={"burn_in": [0.0, 1.0], "values": [0.5, 2.0]})
        assert r.status_code == 200
        assert len(r.json()["scores"]) == 2
