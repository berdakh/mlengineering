"""Checks for the w5d4 challenge: stateful streaming endpoints. SYNTHETIC data only."""
from __future__ import annotations

import pytest

from helpers import error_of, make_samples


def _stream(client, mid, samples):
    out = []
    for s in samples:
        r = client.post(f"/streams/{mid}/samples", json=s)
        assert r.status_code == 200, r.text[:300]
        out.append(r.json())
    return out


def test_register_is_201_then_200(client):
    a = client.put("/streams/pump-1")
    assert a.status_code == 201 and a.json()["created"] is True
    b = client.put("/streams/pump-1")
    assert b.status_code == 200 and b.json()["created"] is False


def test_unknown_machine_is_404(client):
    r = client.post("/streams/ghost/samples", json=make_samples(n=1)[0])
    assert r.status_code == 404 and error_of(r)["code"] == "unknown_machine"
    assert client.get("/streams/ghost").status_code == 404
    assert client.delete("/streams/ghost").status_code == 404


def test_streamed_scores_equal_batch_predict(client):
    samples = make_samples(n=60, seed=1)
    batch = client.post("/predict", json={"machine_id": "pump-2", "samples": samples}).json()["results"]
    client.put("/streams/pump-2")
    streamed = _stream(client, "pump-2", samples)
    for i, (s, b) in enumerate(zip(streamed, batch)):
        assert s["status"] == b["status"] and s["exceeds_threshold"] == b["exceeds_threshold"], i
        if b["score"] is None:
            assert s["score"] is None, i
        else:
            assert s["score"] == pytest.approx(b["score"], rel=1e-9, abs=1e-9), i
    assert streamed[-1]["n_seen"] == 60


def test_out_of_order_is_409_and_harmless(client):
    samples = make_samples(n=40, seed=2)
    client.put("/streams/pump-3")
    _stream(client, "pump-3", samples[:30])
    r = client.post("/streams/pump-3/samples", json=samples[10])
    assert r.status_code == 409 and error_of(r)["code"] == "out_of_order"
    rest = _stream(client, "pump-3", samples[30:])
    assert rest[0]["n_seen"] == 31


def test_duplicates(client):
    samples = make_samples(n=25, seed=3)
    client.put("/streams/pump-4")
    first = _stream(client, "pump-4", samples)[-1]
    again = client.post("/streams/pump-4/samples", json=samples[-1])
    assert again.status_code == 200 and again.json()["duplicate"] is True
    assert again.json()["score"] == first["score"] and again.json()["n_seen"] == first["n_seen"]
    conflict = dict(samples[-1], flow_rate=samples[-1]["flow_rate"] + 1.0)
    r = client.post("/streams/pump-4/samples", json=conflict)
    assert r.status_code == 409 and error_of(r)["code"] == "conflicting_duplicate"


def test_invalid_sample_is_422(client):
    client.put("/streams/pump-5")
    bad = dict(make_samples(n=1)[0], flow_rate=-3.0)
    r = client.post("/streams/pump-5/samples", json=bad)
    assert r.status_code == 422 and error_of(r)["code"] == "validation_error"
    assert client.get("/streams/pump-5").json()["n_seen"] == 0


def test_machines_are_independent(client):
    a, b = make_samples(n=40, seed=4), make_samples(n=40, seed=5, shift_at=25)
    client.put("/streams/a"), client.put("/streams/b")
    inter = {"a": [], "b": []}
    for sa, sb in zip(a, b):
        inter["a"].append(client.post("/streams/a/samples", json=sa).json()["score"])
        inter["b"].append(client.post("/streams/b/samples", json=sb).json()["score"])
    client.put("/streams/a-alone")
    alone = [r["score"] for r in _stream(client, "a-alone", a)]
    assert inter["a"] == alone


def test_state_and_delete(client):
    client.put("/streams/pump-6")
    assert client.get("/streams/pump-6").json()["n_seen"] == 0
    _stream(client, "pump-6", make_samples(n=22, seed=6))
    st = client.get("/streams/pump-6").json()
    assert st["n_seen"] == 22 and st["status"] == "ok"
    d = client.delete("/streams/pump-6")
    assert d.status_code == 204 and d.content == b""
    assert client.post("/streams/pump-6/samples", json=make_samples(n=1)[0]).status_code == 404


def test_invalid_stream_id_is_422(client):
    assert client.put("/streams/" + "x" * 80).status_code == 422
    assert client.put("/streams/-leading-dash").status_code == 422


def test_not_ready_is_503(client_without_model):
    r = client_without_model.put("/streams/pump-7")
    assert r.status_code == 503 and error_of(r)["code"] == "not_ready"
    r = client_without_model.post("/streams/pump-7/samples", json=make_samples(n=1)[0])
    assert r.status_code == 503


def test_lab_behaviour_still_holds(client):
    assert client.get("/readyz").status_code == 200
    r = client.post("/predict", json={"machine_id": "p1", "samples": make_samples(n=30)})
    assert r.status_code == 200 and r.json()["n_samples"] == 30
