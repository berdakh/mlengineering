"""Request validation and response content at the HTTP boundary."""
import pytest

from conftest import MODEL_VERSION, THRESHOLD, body


def test_predict_scores_and_flags(client):
    r = client.post("/predict", json=body(values=[0.0, 2.0, -4.0]))
    assert r.status_code == 200
    data = r.json()
    assert data["scores"] == pytest.approx([0.0, 2.0, 4.0])            # |value - 0| / 1, sign ignored
    assert data["above_threshold"] == [False, False, True]
    assert data["model_version"] == MODEL_VERSION
    assert data["threshold"] == THRESHOLD


def test_one_score_per_value_in_order(client):
    values = [5.0, 0.5, -3.0, 0.0]
    data = client.post("/predict", json=body(values=values)).json()
    assert data["scores"] == pytest.approx([abs(v) for v in values])
    assert len(data["above_threshold"]) == len(values)


def test_population_std_is_used(client):
    # burn-in (0, 2): mean 1, population std 1 (the sample std would be 1.414...)
    data = client.post("/predict", json=body(burn_in=[0.0, 2.0], values=[4.0])).json()
    assert data["scores"] == pytest.approx([3.0])


def test_threshold_is_inclusive(client):
    data = client.post("/predict", json=body(values=[THRESHOLD, -THRESHOLD])).json()
    assert data["above_threshold"] == [True, True]


def test_constant_burn_in_uses_unit_scale(client):
    data = client.post("/predict", json=body(burn_in=[5.0, 5.0], values=[7.0])).json()
    assert data["scores"] == pytest.approx([2.0])


@pytest.mark.parametrize("payload", [
    {"values": [1.0]},                                          # missing burn_in
    {"burn_in": [1.0], "values": [1.0]},                        # burn_in too short
    {"burn_in": [0.0, 1.0], "values": []},                      # nothing to score
    {"burn_in": [0.0, 1.0], "values": ["high"]},                # not a number
    {"burn_in": [0.0, 1.0], "values": [1.0], "burnin": [0.0]},  # unknown (misspelt) field
], ids=["missing-burn-in", "short-burn-in", "empty-values", "string-value", "unknown-field"])
def test_invalid_bodies_are_422(client, payload):
    r = client.post("/predict", json=payload)
    assert r.status_code == 422
    assert all({"loc", "msg", "type"} <= set(e) for e in r.json()["detail"])


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_are_422(client, literal):
    # httpx refuses to encode NaN, but other clients (Python's json module) send it, so send raw bytes.
    raw = '{"burn_in": [0.0, 1.0], "values": [%s]}' % literal
    r = client.post("/predict", content=raw, headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_422_does_not_echo_input(client):
    r = client.post("/predict", json={"burn_in": [0.0, 1.0], "values": ["x" * 50]})
    assert r.status_code == 422
    assert "x" * 50 not in r.text


def test_oversize_batch_is_413(client):
    r = client.post("/predict", json=body(values=[0.0] * 3601))
    assert r.status_code == 413


def test_largest_allowed_batch_is_accepted(client):
    r = client.post("/predict", json=body(values=[0.0] * 3600))
    assert r.status_code == 200
    assert len(r.json()["scores"]) == 3600


def test_version_endpoint(client):
    data = client.get("/version").json()
    assert data["api_schema"] == "flowguard-api/1"
    assert data["model_version"] == MODEL_VERSION
    assert data["package_version"]
