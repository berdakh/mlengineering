"""/metrics: parseable Prometheus text, counters, histograms, gauges, bounded label cardinality."""
from __future__ import annotations

import uuid

from conftest import Exploding, body, parse_metrics, value

REQ = "flowguard_http_requests_total"
LAT = "flowguard_http_request_duration_seconds"


def scrape(client) -> dict:
    r = client.get("/metrics")
    assert r.status_code == 200, f"/metrics answered {r.status_code}"
    assert r.headers.get("content-type", "").startswith("text/plain"), r.headers.get("content-type")
    return parse_metrics(r.text)


def test_metrics_parse_and_name_the_golden_signals(client):
    client.post("/predict", json=body())
    m = scrape(client)
    for name in (REQ, f"{LAT}_bucket", f"{LAT}_count", f"{LAT}_sum", "flowguard_http_requests_in_flight",
                 "flowguard_model_info", "flowguard_prediction_score_count"):
        assert name in m, f"missing metric {name}; have {sorted(m)}"


def test_request_counter_counts_every_outcome(client):
    before = scrape(client)
    for _ in range(3):
        client.post("/predict", json=body())
    for _ in range(2):
        client.post("/predict", json={"machine_id": "x"})
    real = client.app.state.detector
    client.app.state.detector = Exploding()
    client.post("/predict", json=body())
    client.app.state.detector = real
    after = scrape(client)
    for status, n in (("200", 3), ("422", 2), ("500", 1)):
        delta = value(after, REQ, route="/predict", status=status) - value(before, REQ, route="/predict", status=status)
        assert delta == n, f"/predict status {status}: counter rose by {delta}, expected {n}"


def test_latency_histogram_is_cumulative_and_consistent(client):
    before = scrape(client)
    n_before = value(before, f"{LAT}_count", route="/predict")
    for _ in range(4):
        client.post("/predict", json=body())
    client.post("/predict", json={"machine_id": "x"})
    m = scrape(client)
    assert value(m, f"{LAT}_count", route="/predict") - n_before == 5
    buckets = sorted(((float(lab["le"].replace("+Inf", "inf")), v) for lab, v in m[f"{LAT}_bucket"]
                      if lab.get("route") == "/predict"))
    assert buckets and buckets[-1][0] == float("inf"), "a +Inf bucket is required"
    counts = [v for _, v in buckets]
    assert counts == sorted(counts), f"bucket counts must be cumulative (non-decreasing), got {counts}"
    assert counts[-1] == value(m, f"{LAT}_count", route="/predict"), "+Inf bucket must equal _count"
    assert value(m, f"{LAT}_sum", route="/predict") >= 0


def test_score_histogram_counts_scored_samples(client):
    before = value(scrape(client), "flowguard_prediction_score_count")
    r = client.post("/predict", json=body(70))
    scored = sum(x["score"] is not None for x in r.json()["results"])
    after = value(scrape(client), "flowguard_prediction_score_count")
    assert after - before == scored, f"score histogram count rose by {after - before}, expected {scored}"


def test_in_flight_returns_to_baseline_after_errors(client):
    real = client.app.state.detector
    client.app.state.detector = Exploding()
    for _ in range(3):
        client.post("/predict", json=body())
    client.app.state.detector = real
    client.post("/predict", json={"machine_id": "x"})
    client.get("/no/such/route")
    m = scrape(client)
    inflight = value(m, "flowguard_http_requests_in_flight")
    assert 0 <= inflight <= 1, f"in-flight gauge is {inflight} with no request running (only the scrape itself may count)"


def test_model_info_names_the_loaded_version(client, client_without_model):
    m = scrape(client)
    assert value(m, "flowguard_model_info", model_version="synthetic-obs-1") == 1
    m0 = parse_metrics(client_without_model.get("/metrics").text)
    assert all(v == 0 for _, v in m0.get("flowguard_model_info", [])), "no model loaded: no version may report 1"


def test_label_cardinality_is_bounded(client):
    for _ in range(25):
        client.get(f"/devices/{uuid.uuid4().hex}/status")
    for i in range(15):
        client.post("/predict", json=body(), headers={"X-Request-ID": f"card-{i}"})
    m = scrape(client)
    series = m.get(REQ, [])
    assert len(series) <= 12, f"{len(series)} request-counter series after random paths: unbounded labels"
    for labels, _ in series:
        assert set(labels) <= {"method", "route", "status"}, f"unexpected labels {sorted(labels)}"
        assert "/devices/" not in labels.get("route", ""), f"raw path used as a label: {labels}"
    text = client.get("/metrics").text
    assert "card-3" not in text, "request ids must never be metric labels"
