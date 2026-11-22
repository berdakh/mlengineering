"""Added after a customer complained the dashboard felt slow."""
from __future__ import annotations

import time

from conftest import make_samples


def test_predict_is_fast(client):
    body = {"machine_id": "m1", "samples": make_samples(n=600)}
    start = time.perf_counter()
    response = client.post("/predict", json=body)
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 0.5, f"/predict took {elapsed * 1000:.0f} ms"
