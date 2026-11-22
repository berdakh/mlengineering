"""Lab task 2: the reliability contract of /predict, /readyz, /healthz and /metrics."""
from __future__ import annotations

import threading
import time

import pytest

from conftest import BURN, metric

BODY = {"burn_in": BURN, "values": [100.0, 100.3, 150.0, 10.0]}
FALLBACK = [False, False, True, True]          # envelope 20..130


def test_normal_answer(make_client):
    r = make_client().post("/predict", json=BODY, headers={"X-Request-ID": "abc-1"})
    assert r.status_code == 200
    d = r.json()
    assert d["degraded"] is False and d["reason"] is None and d["model_version"] == "synthetic-check-1"
    assert len(d["scores"]) == 4 and d["above_threshold"] == [s >= 3.0 for s in d["scores"]]
    assert d["out_of_support"] == [] and d["request_id"] == "abc-1" and r.headers["X-Request-ID"] == "abc-1"


def test_request_id_generated_when_absent(make_client):
    r = make_client().post("/predict", json=BODY)
    assert r.headers.get("X-Request-ID") and r.json()["request_id"] == r.headers["X-Request-ID"]


@pytest.mark.parametrize("content", ['{"burn_in": [1, 2], "values": [NaN]}',
                                     '{"burn_in": [1, 2], "values": [1], "extra": 1}',
                                     '{"burn_in": [1], "values": [1]}'])
def test_schema_violations_are_422(make_client, content):
    r = make_client().post("/predict", content=content, headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_out_of_support_flagged_scored_and_counted(make_client, events):
    client = make_client()
    d = client.post("/predict", json={**BODY, "values": [-1.0, 0.0, 200.0, 200.5, 100.0]}).json()
    assert d["out_of_support"] == [0, 3]
    assert d["degraded"] is False and d["scores"] is not None and len(d["scores"]) == 5
    assert metric(client.get("/metrics").text, "flowguard_out_of_support_total") == 2
    assert any(e.get("event") == "out_of_support" for e in events())


@pytest.mark.parametrize("faults,reason", [({"model_error": None}, "model_error"),
                                           ({"nan_scores": None}, "invalid_scores"),
                                           ({"slow_model": 1.0}, "deadline")])
def test_model_failure_degrades_explicitly(make_client, events, faults, reason):
    client = make_client(faults)
    t0 = time.perf_counter()
    r = client.post("/predict", json=BODY, headers={"X-Request-ID": f"rid-{reason}"})
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200, f"{reason}: expected a 200 degraded answer, got {r.status_code}"
    assert "NaN" not in r.text and "Infinity" not in r.text
    d = r.json()
    assert d["degraded"] is True and d["reason"] == reason and d["fallback"] == "envelope-rule"
    assert d["scores"] is None and d["above_threshold"] == FALLBACK
    assert metric(client.get("/metrics").text, f'flowguard_degraded_total{{reason="{reason}"}}') == 1
    assert any(e.get("event") == "degraded" and e.get("request_id") == f"rid-{reason}"
               and e.get("reason") == reason for e in events()), "no 'degraded' log event with the request id"
    if reason == "deadline":
        assert elapsed < 0.8, f"the deadline is 0.25 s but the request took {elapsed:.2f} s"


def test_unloadable_model(make_client, tmp_path):
    client = make_client(model_dir=tmp_path / "no-bundle-here")
    assert client.get("/healthz").status_code == 200, "liveness must not fail because the model did"
    ready = client.get("/readyz")
    assert ready.status_code == 503
    assert ready.json()["status"] == "degraded" and ready.json()["fallback"] == "envelope-rule"
    d = client.post("/predict", json=BODY).json()
    assert d["degraded"] is True and d["reason"] == "model_unavailable" and d["above_threshold"] == FALLBACK
    assert d["model_version"] is None


def test_injected_bundle_corrupt_is_the_same_as_unloadable(make_client):
    client = make_client({"bundle_corrupt": None})
    assert client.get("/readyz").status_code == 503
    assert client.post("/predict", json=BODY).json()["reason"] == "model_unavailable"


def test_ready_when_model_loaded(make_client):
    r = make_client().get("/readyz")
    assert r.status_code == 200 and r.json()["status"] == "ready"


def _concurrent(client, n):
    results = []
    lock = threading.Lock()

    def go():
        r = client.post("/predict", json=BODY)
        with lock:
            results.append(r)
    threads = [threading.Thread(target=go) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def test_overload_is_shed_with_retry_after(fg, make_client):
    s = fg["settings"].Settings(deadline_s=3.0, max_inflight=1, retry_after_s=2, support_low=0.0,
                                support_high=200.0, envelope_low=20.0, envelope_high=130.0)
    client = make_client({"slow_model": 0.6}, settings_=s)
    results = _concurrent(client, 3)
    codes = sorted(r.status_code for r in results)
    assert codes.count(429) >= 1, f"no request was shed: {codes}"
    assert codes.count(200) >= 1, f"no request was served: {codes}"
    for r in results:
        if r.status_code == 429:
            assert r.headers.get("Retry-After") == "2"
    text = client.get("/metrics").text
    assert metric(text, "flowguard_shed_total") == codes.count(429)
    assert metric(text, 'flowguard_degraded_total{reason="deadline"}') == 0, "a shed request is not degraded"


def test_slot_is_held_until_the_slow_work_ends(fg, make_client):
    """Bulkhead: after a deadline answer the model call is still running, so its slot is still taken."""
    s = fg["settings"].Settings(deadline_s=0.1, max_inflight=1, retry_after_s=1, support_low=0.0,
                                support_high=200.0, envelope_low=20.0, envelope_high=130.0)
    client = make_client({"slow_model": 0.8}, settings_=s)
    first = client.post("/predict", json=BODY)
    assert first.json()["reason"] == "deadline"
    second = client.post("/predict", json=BODY)
    assert second.status_code == 429, ("the first model call is still running; a second one would exceed "
                                       "max_inflight=1, so it must be shed")
    time.sleep(1.0)
    third = client.post("/predict", json=BODY)
    assert third.status_code == 200, "after the slow call finished the slot must be free again"
