"""Checks for lesson w5d4: the prediction API. SYNTHETIC data, in-process TestClient, no network."""
from __future__ import annotations

import json
import math
import shutil

import pytest

from conftest import N_BURN, as_frame, error_of, make_samples


# --------------------------------------------------------------------------- health, readiness, version
def test_healthz_is_ok_with_and_without_a_model(client, client_without_model):
    for c in (client, client_without_model):
        r = c.get("/healthz")
        assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_readyz_reports_the_model_version(client):
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready" and r.json()["model_version"] == "synthetic-api-1"


def test_app_starts_without_a_model_and_is_not_ready(client_without_model):
    r = client_without_model.get("/readyz")
    assert r.status_code == 503 and error_of(r)["code"] == "not_ready"


def test_corrupt_bundle_is_not_ready(fg, model_dir):
    from fastapi.testclient import TestClient
    (model_dir / "model.json").write_text((model_dir / "model.json").read_text().replace("3.0", "2.0"))
    with TestClient(fg["api"].create_app(model_dir), raise_server_exceptions=False) as c:
        assert c.get("/healthz").status_code == 200
        r = c.get("/readyz")
        assert r.status_code == 503 and error_of(r)["code"] == "not_ready"


def test_version(client, client_without_model):
    v = client.get("/version").json()
    assert v["api_version"] == "1" and v["model_version"] == "synthetic-api-1" and v["package_version"]
    assert client_without_model.get("/version").json()["model_version"] is None


# --------------------------------------------------------------------------- predictions
def test_predict_equals_the_detector(client, detector):
    samples = make_samples(seed=1)
    r = client.post("/predict", json={"machine_id": "pump-07", "samples": samples})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_version"] == "synthetic-api-1" and body["machine_id"] == "pump-07"
    assert body["n_samples"] == len(samples) == len(body["results"])
    assert body["threshold"] == pytest.approx(detector.threshold)
    expected = detector.score_batch(as_frame(samples))
    for i, (res, exp) in enumerate(zip(body["results"], expected)):
        if math.isnan(exp):
            assert res["score"] is None and res["status"] == "warming_up" and res["exceeds_threshold"] is None, i
        else:
            assert res["score"] == pytest.approx(exp, rel=1e-12) and res["status"] == "ok", i
            assert res["exceeds_threshold"] is bool(exp >= detector.threshold), i
    assert any(res["exceeds_threshold"] for res in body["results"][45:]), "the synthetic flow drop should alarm"


def test_fewer_samples_than_the_burn_in_is_not_an_error(client):
    r = client.post("/predict", json={"machine_id": "p1", "samples": make_samples(n=N_BURN - 5)})
    assert r.status_code == 200
    assert all(x["score"] is None and x["status"] == "warming_up" for x in r.json()["results"])


def test_request_id_is_echoed_or_generated(client):
    r = client.post("/predict", json={"machine_id": "p1", "samples": make_samples(n=5)},
                    headers={"X-Request-ID": "trace-abc.123"})
    assert r.headers.get("x-request-id") == "trace-abc.123" and r.json()["request_id"] == "trace-abc.123"
    a, b = client.get("/healthz"), client.get("/healthz")
    assert a.headers.get("x-request-id") and a.headers["x-request-id"] != b.headers.get("x-request-id")
    bad = client.get("/healthz", headers={"X-Request-ID": "x" * 200})
    assert bad.headers.get("x-request-id") and bad.headers["x-request-id"] != "x" * 200


def test_model_is_loaded_once_at_startup(fg, model_dir):
    from fastapi.testclient import TestClient
    with TestClient(fg["api"].create_app(model_dir), raise_server_exceptions=False) as c:
        shutil.rmtree(model_dir)                      # the files are gone; the loaded model is not
        r = c.post("/predict", json={"machine_id": "p1", "samples": make_samples(n=30)})
        assert r.status_code == 200, "predictions must use the model loaded at startup, not reload it"


# --------------------------------------------------------------------------- validation errors (422)
def _bad_request(mutate):
    samples = make_samples(n=30, seed=2)
    body = {"machine_id": "pump-1", "samples": samples}
    mutate(body)
    return body


CASES = {
    "missing_field": (lambda b: b["samples"][3].pop("flow_rate"), ["samples", 3, "flow_rate"], "missing"),
    "extra_field": (lambda b: b["samples"][4].update(rpm=1450), ["samples", 4, "rpm"], "extra_forbidden"),
    "extra_top_level": (lambda b: b.update(debug=True), ["debug"], "extra_forbidden"),
    "above_range": (lambda b: b["samples"][5].update(flow_rate=9999.0), ["samples", 5, "flow_rate"], "less_than_equal"),
    "below_range": (lambda b: b["samples"][6].update(voltage=-1.0), ["samples", 6, "voltage"], "greater_than_equal"),
    "wrong_type": (lambda b: b["samples"][7].update(current="high"), ["samples", 7, "current"], "float_parsing"),
    "bad_timestamp": (lambda b: b["samples"][8].update(timestamp="yesterday"), ["samples", 8, "timestamp"], None),
    "bad_machine_id": (lambda b: b.update(machine_id="pump 1; drop table"), ["machine_id"], "string_pattern_mismatch"),
    "empty_samples": (lambda b: b.update(samples=[]), ["samples"], "too_short"),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_schema_violations_are_422_with_field_paths(client, case):
    mutate, loc_suffix, err_type = CASES[case]
    r = client.post("/predict", json=_bad_request(mutate))
    assert r.status_code == 422, f"{case}: expected 422, got {r.status_code}: {r.text[:300]}"
    err = error_of(r)
    assert err["code"] == "validation_error"
    details = err.get("details") or []
    matching = [d for d in details if list(d.get("loc", []))[-len(loc_suffix):] == loc_suffix]
    assert matching, f"{case}: no detail with a loc ending in {loc_suffix}: {details}"
    if err_type:
        assert any(d.get("type") == err_type for d in matching), f"{case}: expected type {err_type!r}: {matching}"


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_are_rejected_as_such(client, token):
    # Python's json.loads (used by the server) accepts these non-standard tokens, so the API must reject them
    samples = make_samples(n=30, seed=3)
    text = json.dumps({"machine_id": "p1", "samples": samples})
    first = json.dumps(samples[2]["flow_rate"])
    text = text.replace(f'"flow_rate": {first}', f'"flow_rate": {token}', 1)
    r = client.post("/predict", content=text, headers={"content-type": "application/json"})
    assert r.status_code == 422, r.text[:300]
    details = error_of(r)["details"]
    assert any(d["loc"][-1] == "flow_rate" and d["type"] == "finite_number" for d in details), \
        f"a non-finite value must be reported as type 'finite_number', got {details}"


def test_oversize_batch_is_422(client, fg):
    limit = fg["schemas"].MAX_SAMPLES
    one = make_samples(n=1)[0]
    r = client.post("/predict", json={"machine_id": "p1", "samples": [one] * (limit + 1)})
    assert r.status_code == 422
    assert any(d["loc"][-1] == "samples" and d["type"] == "too_long" for d in error_of(r)["details"])


def test_malformed_json_is_422(client):
    r = client.post("/predict", content='{"machine_id": "p1", "samples": [', headers={"content-type": "application/json"})
    assert r.status_code == 422 and error_of(r)["code"] == "validation_error"


# --------------------------------------------------------------------------- domain errors and failures
@pytest.mark.parametrize("kind", ["duplicate", "reversed"])
def test_non_increasing_timestamps_are_400(client, kind):
    samples = make_samples(n=30, seed=4)
    if kind == "duplicate":
        samples[10]["timestamp"] = samples[9]["timestamp"]
    else:
        samples[10]["timestamp"], samples[11]["timestamp"] = samples[11]["timestamp"], samples[10]["timestamp"]
    r = client.post("/predict", json={"machine_id": "p1", "samples": samples})
    assert r.status_code == 400, r.text[:300]
    err = error_of(r)
    assert err["code"] == "invalid_sequence"
    assert any(d["loc"][-3:] == ["samples", 10, "timestamp"] or d["loc"][-3:] == ["samples", 11, "timestamp"]
               for d in err["details"]), err["details"]


def test_predict_without_a_model_is_503(client_without_model):
    r = client_without_model.post("/predict", json={"machine_id": "p1", "samples": make_samples(n=10)})
    assert r.status_code == 503 and error_of(r)["code"] == "not_ready"


def test_internal_errors_do_not_leak(client):
    class Exploding:
        version, threshold = "synthetic-api-1", 3.0

        def score_batch(self, frame):
            raise RuntimeError("SECRET-db-password at /srv/models/internal.py line 42")

    client.app.state.detector = Exploding()
    r = client.post("/predict", json={"machine_id": "p1", "samples": make_samples(n=25)},
                    headers={"X-Request-ID": "req-500"})
    assert r.status_code == 500
    err = error_of(r)
    assert err["code"] == "internal_error" and err["request_id"] == "req-500"
    assert "SECRET" not in r.text and "Traceback" not in r.text and "internal.py" not in r.text


def test_unknown_route_uses_the_error_body(client):
    r = client.get("/no-such-thing")
    assert r.status_code == 404 and error_of(r)["code"] == "not_found"
    r = client.get("/predict")
    assert r.status_code == 405 and error_of(r)["code"] == "method_not_allowed"


# --------------------------------------------------------------------------- the published contract
def test_openapi_documents_the_constraints(client, fg):
    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    sample, request = schemas["Sample"], schemas["PredictRequest"]
    assert sample.get("additionalProperties") is False and request.get("additionalProperties") is False
    assert request["properties"]["samples"].get("maxItems") == fg["schemas"].MAX_SAMPLES
    flow = sample["properties"]["flow_rate"]
    assert flow.get("maximum") == fg["schemas"].SENSOR_LIMITS["flow_rate"][1]
    assert "/predict" in spec["paths"] and "/readyz" in spec["paths"]


def test_mixed_timezone_awareness_is_400_not_500(client):
    samples = make_samples(n=30, seed=5)
    samples[12]["timestamp"] = samples[12]["timestamp"] + "+00:00"
    r = client.post("/predict", json={"machine_id": "p1", "samples": samples})
    assert r.status_code == 400 and error_of(r)["code"] == "invalid_sequence", r.text[:300]
