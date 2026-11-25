"""Structured logs: one JSON line per event, request ids, access and prediction events, no raw data."""
from __future__ import annotations

import json
import logging

from conftest import MARKER_VALUES, Exploding, body, log_events

ACCESS_KEYS = ("request_id", "method", "route", "status", "duration_ms", "model_version")


def test_formatter_writes_one_json_line_with_fields(fg):
    fmt = fg["observability"].JsonFormatter()
    rec = logging.LogRecord("flowguard.test", logging.INFO, __file__, 1, "something_happened", None, None)
    rec.fields = {"request_id": "r-1", "n": 3, "note": "line one\nline two"}
    out = fmt.format(rec)
    assert "\n" not in out, "a log record must be exactly one line"
    obj = json.loads(out)
    for key in ("ts", "level", "logger", "event"):
        assert key in obj, f"missing key {key!r} in {obj}"
    assert obj["event"] == "something_happened" and obj["level"] == "INFO" and obj["logger"] == "flowguard.test"
    assert obj["request_id"] == "r-1" and obj["n"] == 3 and obj["note"] == "line one\nline two"


def test_formatter_records_exception_type(fg):
    fmt = fg["observability"].JsonFormatter()
    try:
        raise KeyError("x")
    except KeyError:
        import sys
        rec = logging.LogRecord("flowguard.test", logging.ERROR, __file__, 1, "boom", None, sys.exc_info())
    obj = json.loads(fmt.format(rec))
    assert obj.get("exc_type") == "KeyError"


def test_every_response_carries_a_request_id(client):
    responses = [client.post("/predict", json=body()), client.post("/predict", json={"machine_id": "x"}),
                 client.get("/healthz"), client.get("/no/such/route")]
    ids = [r.headers.get("x-request-id") for r in responses]
    assert all(ids), f"every response needs X-Request-ID, got {ids}"
    assert len(set(ids)) == len(ids), "generated request ids must be unique"


def test_incoming_request_id_is_propagated_and_bad_ones_replaced(client):
    r = client.post("/predict", json=body(), headers={"X-Request-ID": "client-abc.123"})
    assert r.headers.get("x-request-id") == "client-abc.123"
    assert r.json()["request_id"] == "client-abc.123"
    bad = "not ok id with spaces " + "x" * 80
    r = client.get("/healthz", headers={"X-Request-ID": bad})
    assert r.headers.get("x-request-id") not in (None, "", bad), "an invalid incoming id must be replaced"


def _access_for(events, rid):
    return [e for e in events if e.get("event") == "access" and e.get("request_id") == rid]


def test_exactly_one_access_line_per_request_for_every_outcome(client, logbuf):
    client.app.state.detector = client.app.state.detector  # model loaded
    outcomes = {}
    outcomes[200] = client.post("/predict", json=body(), headers={"X-Request-ID": "ok-1"})
    outcomes[422] = client.post("/predict", json={"machine_id": "x"}, headers={"X-Request-ID": "bad-1"})
    outcomes[404] = client.get("/no/such/route", headers={"X-Request-ID": "nf-1"})
    real = client.app.state.detector
    client.app.state.detector = Exploding()
    outcomes[500] = client.post("/predict", json=body(), headers={"X-Request-ID": "err-1"})
    client.app.state.detector = real
    events = log_events(logbuf)
    for status, resp in outcomes.items():
        assert resp.status_code == status, f"expected {status}, got {resp.status_code}"
        rid = resp.headers.get("x-request-id")
        lines = _access_for(events, rid)
        assert len(lines) == 1, f"status {status}: expected exactly one access event for {rid}, got {len(lines)}"
        line = lines[0]
        for key in ACCESS_KEYS:
            assert key in line, f"status {status}: access event lacks {key!r}: {line}"
        assert int(line["status"]) == status
        assert isinstance(line["duration_ms"], (int, float)) and line["duration_ms"] >= 0
    assert _access_for(events, "err-1")[0]["level"] in ("WARNING", "ERROR"), "a 5xx access line should not be INFO"


def test_not_ready_service_logs_503(client_without_model, logbuf):
    r = client_without_model.post("/predict", json=body())
    assert r.status_code == 503
    lines = _access_for(log_events(logbuf), r.headers.get("x-request-id"))
    assert len(lines) == 1 and int(lines[0]["status"]) == 503


def test_prediction_event_summarises_the_request(client, logbuf):
    r = client.post("/predict", json=body(80), headers={"X-Request-ID": "pred-1"})
    assert r.status_code == 200
    results = r.json()["results"]
    preds = [e for e in log_events(logbuf) if e.get("event") == "prediction" and e.get("request_id") == "pred-1"]
    assert len(preds) == 1, f"expected one prediction event, got {len(preds)}"
    p = preds[0]
    assert p.get("model_version") == "synthetic-obs-1" and p.get("machine_id") == "pump-07"
    assert p.get("n_samples") == 80
    assert p.get("n_scored", -1) + p.get("n_warming_up", -1) == 80
    assert p.get("n_exceeding") == sum(bool(x["exceeds_threshold"]) for x in results)
    best = max(x["score"] for x in results if x["score"] is not None)
    assert abs(float(p.get("max_score")) - best) < 1e-3


def test_raw_sample_values_are_never_logged(client, logbuf):
    r = client.post("/predict", json=body(60, markers=True), headers={"X-Request-ID": "raw-1"})
    assert r.status_code == 200
    bad = dict(body(30, markers=True))
    bad["samples"][5]["pressure"] = 999.123456      # out of range -> 422
    client.post("/predict", json=bad)
    text = logbuf.getvalue()
    for marker in (*MARKER_VALUES, 999.123456):
        assert str(marker) not in text, f"raw sample value {marker} appears in the logs"
    for e in log_events(logbuf):
        assert "samples" not in e, f"an event carries the request samples: keys {sorted(e)}"


def test_summarise_samples_has_counts_not_values(fg):
    from flowguard.schemas import PredictRequest
    req = PredictRequest(**body(25, markers=True))
    summary = fg["observability"].summarise_samples(req.samples)
    assert summary.get("n_samples") == 25
    assert all(str(m) not in json.dumps(summary, default=str) for m in MARKER_VALUES)
