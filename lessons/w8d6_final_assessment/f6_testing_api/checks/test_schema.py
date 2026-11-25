"""Part 2: the request schema accepts valid payloads and rejects invalid ones."""
import importlib.util

import pytest
from pydantic import ValidationError

from f6_paths import TARGET

VALID = {"account_id": "A00042", "tier": "business", "tenure_days": 400, "shipments_30d": 6, "monthly_fee": 149.0}


@pytest.fixture(scope="module")
def ScoreRequest():
    spec = importlib.util.spec_from_file_location("submitted_schemas_f6", TARGET / "schemas.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ScoreRequest


def test_valid_payload(ScoreRequest):
    req = ScoreRequest(**VALID)
    assert req.account_id == "A00042" and req.shipments_30d == 6
    assert req.avg_parcel_kg is None, "avg_parcel_kg is optional and defaults to None"


def test_optional_field_given(ScoreRequest):
    assert ScoreRequest(**VALID, avg_parcel_kg=3.5).avg_parcel_kg == pytest.approx(3.5)


def test_boundary_values_accepted(ScoreRequest):
    ScoreRequest(**{**VALID, "tenure_days": 0, "shipments_30d": 0, "monthly_fee": 1000, "avg_parcel_kg": 70})


@pytest.mark.parametrize("change", [
    {"tenure_days": -1},
    {"shipments_30d": -3},
    {"monthly_fee": 0},
    {"monthly_fee": -49.0},
    {"monthly_fee": 1000.5},
    {"tier": "platinum"},
    {"account_id": ""},
    {"account_id": "42"},
    {"account_id": "A123456"},
    {"account_id": "C00042"},
    {"avg_parcel_kg": 0},
    {"avg_parcel_kg": 70.5},
    {"shipments_30d": "many"},
    {"avg_parcel_k": 3.0},          # misspelt optional field must not be silently ignored
], ids=lambda c: next(iter(c)) + "=" + repr(next(iter(c.values()))))
def test_invalid_payload_rejected(ScoreRequest, change):
    with pytest.raises(ValidationError):
        ScoreRequest(**{**VALID, **change})


@pytest.mark.parametrize("missing", ["account_id", "tier", "tenure_days", "shipments_30d", "monthly_fee"])
def test_required_fields(ScoreRequest, missing):
    payload = {k: v for k, v in VALID.items() if k != missing}
    with pytest.raises(ValidationError):
        ScoreRequest(**payload)
