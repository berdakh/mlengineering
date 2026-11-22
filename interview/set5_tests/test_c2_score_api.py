"""C2: a checkout risk-scoring endpoint. Behaviour from the contract in interview/set5_system_design.md."""
import json

import pytest
from fastapi.testclient import TestClient

CALLS = []


def fake_model(amount, customer_age_days, n_items):
    CALLS.append((amount, customer_age_days, n_items))
    return round(0.001 * amount + 0.01 * n_items - 0.0001 * customer_age_days, 6)


def valid(**overrides):
    body = {"application_id": "app-001", "amount": 120.0, "currency": "EUR",
            "customer_age_days": 400,
            "items": [{"sku": "A-1", "price": 100.0}, {"sku": "B-2", "price": 20.0}]}
    body.update(overrides)
    return body


@pytest.fixture()
def client(c2):
    with TestClient(c2.create_app(fake_model), raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def cold_client(c2):
    with TestClient(c2.create_app(None), raise_server_exceptions=False) as c:
        yield c


def raw_post(client, text):
    return client.post("/score", content=text, headers={"content-type": "application/json"})


def test_valid_request_scores_with_the_model(client):
    CALLS.clear()
    r = client.post("/score", json=valid())
    assert r.status_code == 200
    body = r.json()
    assert body["application_id"] == "app-001"
    assert body["score"] == pytest.approx(0.001 * 120 + 0.02 - 0.04)
    assert isinstance(body["model_version"], str) and body["model_version"]
    assert CALLS == [(120.0, 400, 2)]


@pytest.mark.parametrize("field,value", [
    ("amount", 0), ("amount", -5.0), ("amount", 5000.01),
    ("currency", "JPY"), ("customer_age_days", -1), ("items", []),
    ("application_id", ""),
])
def test_schema_violations_are_422_with_the_field_path(client, field, value):
    r = client.post("/score", json=valid(**{field: value}))
    assert r.status_code == 422, (field, value, r.status_code)
    body = r.json()
    assert body["error"] == "validation_error"
    assert any(field in [str(p) for p in d["loc"]] for d in body["details"])


def test_too_many_items_is_422(client):
    items = [{"sku": f"S{i}", "price": 1.0} for i in range(51)]
    assert client.post("/score", json=valid(amount=51.0, items=items)).status_code == 422


def test_nested_item_constraint_is_reported_with_its_path(client):
    body = valid(items=[{"sku": "A-1", "price": 120.0}, {"sku": "B-2", "price": 0}])
    r = client.post("/score", json=body)
    assert r.status_code == 422
    locs = [[str(p) for p in d["loc"]] for d in r.json()["details"]]
    assert any("items" in loc and "price" in loc for loc in locs)


def test_unknown_field_is_rejected_not_ignored(client):
    r = client.post("/score", json=valid(amount_usd=120.0))
    assert r.status_code == 422
    assert any("amount_usd" in [str(p) for p in d["loc"]] for d in r.json()["details"])


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_amount_is_422_not_500_and_not_echoed(client, token):
    text = json.dumps(valid()).replace('"amount": 120.0', f'"amount": {token}')
    r = raw_post(client, text)
    assert r.status_code == 422
    assert token not in r.text            # the input is not echoed back
    types = [d["type"] for d in r.json()["details"]]
    assert "finite_number" in types       # reported as what it is, not as "too large"


def test_validation_error_body_does_not_echo_the_input(client):
    # The offending value itself must not come back: inputs can hold personal data or huge payloads.
    r = client.post("/score", json=valid(currency="card-4111-1111"))
    assert r.status_code == 422
    assert "card-4111-1111" not in r.text


def test_amount_mismatch_is_a_domain_error_400(client):
    r = client.post("/score", json=valid(amount=150.0))
    assert r.status_code == 400
    assert r.json()["error"] == "amount_mismatch"


def test_mismatch_within_one_cent_is_accepted(client):
    assert client.post("/score", json=valid(amount=120.005)).status_code == 200


def test_not_ready_is_503(cold_client):
    r = cold_client.post("/score", json=valid())
    assert r.status_code == 503
    assert r.json()["error"] == "not_ready"


def test_validation_runs_before_readiness(cold_client):
    assert cold_client.post("/score", json=valid(currency="JPY")).status_code == 422


def test_wrong_method_is_405(client):
    assert client.get("/score").status_code == 405
