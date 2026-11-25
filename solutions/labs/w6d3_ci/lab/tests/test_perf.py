"""Wall-clock check. Marked ``perf``: excluded from the per-push gate by ``addopts`` in pyproject.toml
and run by the scheduled workflow instead (see the lesson, section 2.5)."""
from __future__ import annotations

import time

import pytest
from conftest import make_samples


@pytest.mark.perf
def test_predict_600_samples_under_200_ms(client):
    body = {"machine_id": "m1", "samples": make_samples(n=600)}
    client.post("/predict", json=body)  # warm-up
    durations = []
    for _ in range(5):
        start = time.perf_counter()
        assert client.post("/predict", json=body).status_code == 200
        durations.append(time.perf_counter() - start)
    assert sorted(durations)[2] < 0.200, f"median {sorted(durations)[2] * 1000:.0f} ms"
