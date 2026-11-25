"""Failure-injection drills as tests: every failure the service claims to handle is produced here.

Run from the lab directory:  PYTHONPATH=src python -m pytest tests -q
"""
from __future__ import annotations

import threading

import pytest

from conftest import BODY


def test_normal_answer_is_not_degraded(make_client):
    r = make_client().post("/predict", json=BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["degraded"] is False and data["scores"] is not None
    assert data["above_threshold"] == [s >= 3.0 for s in data["scores"]]


def test_out_of_support_values_are_flagged_and_counted(make_client):
    client = make_client()
    body = {**BODY, "values": [100.0, 250.0, -5.0]}
    data = client.post("/predict", json=body).json()
    assert data["out_of_support"] == [1, 2]
    assert "flowguard_out_of_support_total 2" in client.get("/metrics").text


@pytest.mark.parametrize("faults,reason", [({"model_error": None}, "model_error"),
                                           ({"nan_scores": None}, "invalid_scores"),
                                           ({"slow_model": 1.0}, "deadline")])
def test_model_failures_degrade_explicitly(make_client, faults, reason):
    client = make_client(faults)
    r = client.post("/predict", json=BODY, headers={"X-Request-ID": "drill-1"})
    assert r.status_code == 200
    data = r.json()
    assert data["degraded"] is True and data["reason"] == reason and data["scores"] is None
    assert data["above_threshold"] == [False, False, True, True]          # envelope rule 20..130
    assert f'flowguard_degraded_total{{reason="{reason}"}} 1' in client.get("/metrics").text
    assert r.headers["X-Request-ID"] == "drill-1"


def test_unloadable_bundle_keeps_liveness_and_fails_readiness(make_client, tmp_path):
    client = make_client(model_dir=tmp_path / "missing")
    assert client.get("/healthz").status_code == 200
    ready = client.get("/readyz")
    assert ready.status_code == 503 and ready.json()["status"] == "degraded"
    data = client.post("/predict", json=BODY).json()
    assert data["degraded"] is True and data["reason"] == "model_unavailable"


def test_overload_is_shed_with_retry_after(make_client):
    from flowguard.settings import Settings
    settings = Settings(deadline_s=2.0, max_inflight=1, retry_after_s=3,
                        support_low=0.0, support_high=200.0, envelope_low=20.0, envelope_high=130.0)
    client = make_client({"slow_model": 0.6}, settings=settings)
    results = []
    threads = [threading.Thread(target=lambda: results.append(client.post("/predict", json=BODY)))
               for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) >= 1 and codes.count(429) >= 1
    shed = [r for r in results if r.status_code == 429]
    assert all(r.headers["Retry-After"] == "3" for r in shed)
