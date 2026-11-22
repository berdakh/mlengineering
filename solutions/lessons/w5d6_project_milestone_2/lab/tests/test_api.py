import pytest
from fastapi.testclient import TestClient

from flowguard import __version__
from flowguard.api import create_app


@pytest.fixture
def client(bundle_dir):
    with TestClient(create_app(bundle_dir)) as c:
        yield c


def test_predict(client):
    data = client.post("/predict", json={"burn_in": [-1.0, 1.0], "values": [3.0, -0.5]}).json()
    assert data["scores"] == pytest.approx([3.0, 0.5])
    assert data["above_threshold"] == [True, False]
    assert data["model_version"] == "test-model"


def test_version_and_readiness(client):
    assert client.get("/readyz").status_code == 200
    assert client.get("/version").json()["package_version"] == __version__


def test_invalid_and_unready(client, tmp_path):
    assert client.post("/predict", json={"burn_in": [1.0], "values": [1.0]}).status_code == 422
    (tmp_path / "empty").mkdir()
    with TestClient(create_app(tmp_path / "empty")) as c:
        assert c.get("/readyz").status_code == 503
        assert c.post("/predict", json={"burn_in": [0.0, 1.0], "values": [1.0]}).status_code == 503
