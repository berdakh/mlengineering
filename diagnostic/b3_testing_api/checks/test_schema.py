"""Part 2: the request schema accepts valid payloads and rejects invalid ones."""
import importlib.util

import pytest
from pydantic import ValidationError

from b3_paths import TARGET

VALID = {"customer_id": "C00042", "plan": "premium", "tenure_days": 120, "sessions_30d": 14, "monthly_price": 19.99}


@pytest.fixture(scope="module")
def PredictRequest():
    spec = importlib.util.spec_from_file_location("submitted_schemas", TARGET / "schemas.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PredictRequest


def test_valid_payload(PredictRequest):
    req = PredictRequest(**VALID)
    assert req.customer_id == "C00042" and req.tenure_days == 120
    assert req.avg_session_min is None, "avg_session_min is optional and defaults to None"


def test_optional_field_given(PredictRequest):
    assert PredictRequest(**VALID, avg_session_min=31.5).avg_session_min == pytest.approx(31.5)


def test_boundary_values_accepted(PredictRequest):
    PredictRequest(**{**VALID, "tenure_days": 0, "sessions_30d": 0, "monthly_price": 500, "avg_session_min": 0})


@pytest.mark.parametrize("change", [
    {"tenure_days": -5},
    {"sessions_30d": -1},
    {"monthly_price": 0},
    {"monthly_price": -9.99},
    {"monthly_price": 500.01},
    {"plan": "gold"},
    {"customer_id": ""},
    {"customer_id": "42"},
    {"customer_id": "C123456"},
    {"avg_session_min": -1.0},
    {"tenure_days": "a long time"},
    {"avg_sesion_min": 30.0},          # misspelt optional field must not be silently ignored
], ids=lambda c: next(iter(c)) + "=" + repr(next(iter(c.values()))))
def test_invalid_payload_rejected(PredictRequest, change):
    with pytest.raises(ValidationError):
        PredictRequest(**{**VALID, **change})


@pytest.mark.parametrize("missing", ["customer_id", "plan", "tenure_days", "sessions_30d", "monthly_price"])
def test_required_fields(PredictRequest, missing):
    payload = {k: v for k, v in VALID.items() if k != missing}
    with pytest.raises(ValidationError):
        PredictRequest(**payload)
