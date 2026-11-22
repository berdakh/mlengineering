"""Determinism under concurrent load. Sequential tests cannot see shared-state bugs."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from conftest import body


def test_concurrent_requests_get_their_own_answers(client):
    def call(i: int) -> tuple[int, list[float]]:
        r = client.post("/predict", json=body(values=[float(i)] * 5))
        assert r.status_code == 200
        return i, r.json()["scores"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(call, range(48)))
    for i, scores in results:
        assert scores == pytest.approx([float(i)] * 5), f"request {i} received another request's scores"
