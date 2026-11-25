"""Tests for eta_service.py, one per layer of the contract. Run from the repository root:

    python -m pytest labs/w5d5_api_testing/example/test_eta_service.py -q
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eta_service import create_app  # noqa: E402


@pytest.fixture
def config_path(tmp_path):                       # every test gets its own artifact on disk
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": "cfg-7", "handling_min": 5.0}))
    return path


@pytest.fixture(params=[False, True], ids=["correct", "buggy-cache"])
def client(request, config_path):
    # Parametrised over both variants so you can watch which tests catch the defect.
    with TestClient(create_app(config_path, buggy_cache=request.param)) as c:    # `with` runs startup
        yield c


def test_happy_path(client):
    r = client.post("/eta", json={"distance_km": 30, "recent_speeds_kmh": [50, 60, 70]})
    assert r.status_code == 200
    assert r.json() == {"eta_min": pytest.approx(35.0), "config_version": "cfg-7"}   # 30/60*60 + 5


@pytest.mark.parametrize("payload", [
    {"distance_km": 0, "recent_speeds_kmh": [50]},              # gt=0
    {"distance_km": 10, "recent_speeds_kmh": []},              # min_length=1
    {"distance_km": 10, "recent_speeds_kmh": [50], "x": 1},    # extra field
])
def test_bad_input_is_422(client, payload):
    assert client.post("/eta", json=payload).status_code == 422


def test_nan_is_422_not_500(client):
    raw = '{"distance_km": 10, "recent_speeds_kmh": [NaN]}'
    r = client.post("/eta", content=raw, headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_not_ready_without_startup(config_path):
    plain = TestClient(create_app(config_path))   # no `with`: lifespan never ran
    assert plain.get("/readyz").status_code == 503


def test_concurrent_requests_are_isolated(client):
    def call(speed):
        r = client.post("/eta", json={"distance_km": 60, "recent_speeds_kmh": [speed]})
        return speed, r.json()["eta_min"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(call, range(10, 58)))
    wrong = [(s, eta) for s, eta in results if eta != pytest.approx(60 / s * 60 + 5)]
    assert not wrong, f"{len(wrong)} of {len(results)} responses belong to another request"
