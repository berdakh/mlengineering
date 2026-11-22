import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))

from flowguard.api import create_app  # noqa: E402
from flowguard.bundle import save_bundle  # noqa: E402
from flowguard.scoring import ZScoreModel  # noqa: E402

OK = {"burn_in": [0.0, 1.0], "values": [0.5]}


@pytest.fixture
def bundle(tmp_path):
    return save_bundle(ZScoreModel("flow_rate", 100, 3.0, 30, 10, "v1"), tmp_path / "b")


@pytest.fixture
def client(bundle):
    with TestClient(create_app(bundle)) as c:
        yield c


def test_ok(client):
    assert client.post("/predict", json=OK).status_code == 200
    assert client.get("/readyz").status_code == 200
    assert client.get("/version").status_code == 200


@pytest.mark.parametrize("payload", [{"values": [1.0]}, {"burn_in": [0.0, 1.0], "values": []},
                                     {"burn_in": [0.0, 1.0], "values": [1.0], "extra": 1}])
def test_422(client, payload):
    assert client.post("/predict", json=payload).status_code == 422


def test_nan_422(client):
    raw = '{"burn_in": [0.0, 1.0], "values": [NaN]}'
    assert client.post("/predict", content=raw, headers={"content-type": "application/json"}).status_code == 422


def test_413(client):
    assert client.post("/predict", json={"burn_in": [0.0, 1.0], "values": [0.0] * 3601}).status_code == 413


def test_503_without_model(tmp_path):
    (tmp_path / "e").mkdir()
    with TestClient(create_app(tmp_path / "e")) as c:
        assert c.get("/readyz").status_code == 503
        assert c.post("/predict", json=OK).status_code == 503


def test_tampered(bundle):
    f = bundle / "model.json"
    p = json.loads(f.read_text())
    p["threshold"] = 0.0
    f.write_text(json.dumps(p))
    with TestClient(create_app(bundle)) as c:
        assert c.get("/readyz").status_code == 503
