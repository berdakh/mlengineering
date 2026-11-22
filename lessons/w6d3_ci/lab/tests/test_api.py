"""API tests run on every push (fast, deterministic, no network, no downloaded data)."""
from __future__ import annotations

import pandas as pd
from conftest import N_BURN, make_samples

from flowguard.bundle import load_bundle


def test_health_and_ready(client):
    assert client.get("/healthz").status_code == 200
    ready = client.get("/readyz")
    assert ready.status_code == 200 and ready.json()["model_version"] == "test-1"


def test_predict_matches_detector(client, model_dir):
    samples = make_samples()
    r = client.post("/predict", json={"machine_id": "m1", "samples": samples})
    assert r.status_code == 200
    body = r.json()
    assert body["model_version"] == "test-1" and body["n_samples"] == len(samples)
    detector, _ = load_bundle(model_dir)
    frame = pd.DataFrame(samples).rename(columns={"timestamp": "datetime"})
    expected = detector.score_batch(frame)
    for res, exp in zip(body["results"], expected, strict=True):
        if res["status"] == "warming_up":
            assert pd.isna(exp)
        else:
            assert abs(res["score"] - exp) < 1e-12


def test_warm_up_and_alarm(client):
    results = client.post("/predict", json={"machine_id": "m1", "samples": make_samples()}).json()["results"]
    assert all(r["status"] == "warming_up" for r in results[:N_BURN])
    assert any(r["exceeds_threshold"] for r in results[45:])


def test_invalid_input_is_422(client):
    bad = make_samples()
    bad[3]["flow_rate"] = -1.0
    r = client.post("/predict", json={"machine_id": "m1", "samples": bad})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_not_ready_without_model(tmp_path):
    from fastapi.testclient import TestClient

    from flowguard.api import create_app
    with TestClient(create_app(tmp_path / "missing"), raise_server_exceptions=False) as c:
        assert c.get("/healthz").status_code == 200
        assert c.get("/readyz").status_code == 503
