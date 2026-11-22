"""Your failure-injection suite (lab task 4). One example is given; it is not enough.

Run from the lab directory:  PYTHONPATH=src python -m pytest tests -q
Write one test per failure the service claims to handle (see the contract in src/flowguard/api.py).
The checks run THIS suite against your service (it must pass) and against broken services (it must fail).
"""
from __future__ import annotations

from conftest import BODY


def test_normal_answer_is_not_degraded(make_client):
    r = make_client().post("/predict", json=BODY)
    assert r.status_code == 200
    assert r.json()["degraded"] is False
