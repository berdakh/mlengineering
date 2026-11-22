"""How often does the buggy cache answer with another request's data? Run from the repository root:

    python lessons/w5d5_api_testing/example/race_demo.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eta_service import create_app  # noqa: E402

N_REQUESTS = 96


def wrong_fraction(buggy: bool, threads: int) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "c.json"
        cfg.write_text(json.dumps({"version": "cfg-7", "handling_min": 5.0}))
        with TestClient(create_app(cfg, buggy_cache=buggy)) as client:
            def call(i: int) -> bool:
                speed = 10.0 + i
                eta = client.post("/eta", json={"distance_km": 60, "recent_speeds_kmh": [speed]}).json()["eta_min"]
                return abs(eta - (60 / speed * 60 + 5)) > 1e-6
            with ThreadPoolExecutor(max_workers=threads) as pool:
                return sum(pool.map(call, range(N_REQUESTS))) / N_REQUESTS


def table(thread_counts=(1, 2, 4, 8, 16)) -> list[tuple[int, float, float]]:
    return [(t, wrong_fraction(False, t), wrong_fraction(True, t)) for t in thread_counts]


if __name__ == "__main__":
    print(f"fraction of {N_REQUESTS} responses that belong to another request")
    print(f"{'threads':>7}  {'correct':>8}  {'buggy cache':>11}")
    for t, ok, bad in table():
        print(f"{t:>7}  {ok:>8.2f}  {bad:>11.2f}")
