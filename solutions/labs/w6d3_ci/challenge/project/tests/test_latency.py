"""Wall-clock check, moved to the slow lane (REFERENCE SOLUTION, w6d3 challenge).

It is marked ``perf``, which pyproject.toml's addopts exclude from the per-push run; the scheduled
workflow ``perf.yml`` runs it with ``-m perf``. It takes the median of five warm requests and allows
200 ms, a budget with headroom on a shared runner. A latency regression is a trend to watch on a
schedule, not a reason to block every push on a machine whose speed nobody controls.
"""
from __future__ import annotations

import time

import pytest
from conftest import make_samples


@pytest.mark.perf
def test_predict_600_samples_median_under_200_ms(client):
    body = {"machine_id": "m1", "samples": make_samples(n=600)}
    assert client.post("/predict", json=body).status_code == 200  # warm-up
    durations = []
    for _ in range(5):
        start = time.perf_counter()
        assert client.post("/predict", json=body).status_code == 200
        durations.append(time.perf_counter() - start)
    median = sorted(durations)[2]
    assert median < 0.200, f"median /predict {median * 1000:.0f} ms"
