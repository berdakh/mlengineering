"""Startup, readiness and degraded operation."""
import json

from fastapi.testclient import TestClient

from conftest import MODEL_VERSION, body
from flowguard.api import create_app


def test_ready_after_startup(client):
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["model_version"] == MODEL_VERSION


def test_not_ready_before_startup(bundle_dir):
    client = TestClient(create_app(bundle_dir))        # no `with`: the lifespan has not run
    assert client.get("/readyz").status_code == 503


def test_missing_bundle_starts_degraded(degraded_client):
    assert degraded_client.get("/healthz").status_code == 200
    r = degraded_client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["reason"]
    assert degraded_client.post("/predict", json=body()).status_code == 503
    assert degraded_client.get("/version").json()["model_version"] is None


def test_tampered_bundle_is_refused(bundle_dir):
    model_file = bundle_dir / "model.json"
    params = json.loads(model_file.read_text())
    params["threshold"] = 0.0                          # an edit after packaging
    model_file.write_text(json.dumps(params))
    with TestClient(create_app(bundle_dir)) as client:
        assert client.get("/readyz").status_code == 503
        assert client.post("/predict", json=body()).status_code == 503
