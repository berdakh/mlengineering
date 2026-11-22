"""Send the same requests to the naive and the careful version of tiny_api (in process, no network).

    python lessons/w5d4_fastapi_validation/example/demo_requests.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402

from tiny_api import careful_app, naive_app  # noqa: E402

CASES = [
    ("valid", {"readings": [{"temperature_c": 23.5, "humidity_pct": 50}]}),
    ("string number '23.5'", {"readings": [{"temperature_c": "23.5", "humidity_pct": 50}]}),
    ("humidity 4500 (per-mille sent as percent)", {"readings": [{"temperature_c": 23.5, "humidity_pct": 4500}]}),
    ("extra field 'co2'", {"readings": [{"temperature_c": 23.5, "humidity_pct": 50, "co2": 900}]}),
    ("missing humidity", {"readings": [{"temperature_c": 23.5}]}),
    ("empty list", {"readings": []}),
]


def show(name: str, response) -> None:
    text = response.text if len(response.text) < 150 else response.text[:147] + "..."
    print(f"  {name:<44} {response.status_code}  {text}")


def main() -> None:
    with TestClient(naive_app(), raise_server_exceptions=False) as naive, \
            TestClient(careful_app(), raise_server_exceptions=False) as careful:
        print("NAIVE (body is a bare list of readings)")
        for name, body in CASES:
            show(name, naive.post("/comfort", json=body["readings"]))
        show("NaN temperature", naive.post("/comfort", content='[{"temperature_c": NaN, "humidity_pct": 50}]',
                                           headers={"content-type": "application/json"}))
        print("\nCAREFUL")
        for name, body in CASES:
            show(name, careful.post("/comfort", json=body))
        show("NaN temperature", careful.post("/comfort",
                                             content='{"readings": [{"temperature_c": NaN, "humidity_pct": 50}]}',
                                             headers={"content-type": "application/json"}))
        careful.app.state.coeffs = {"a": 4.0}                 # simulate a bug: a coefficient is missing
        show("internal bug (missing coefficient)", careful.post("/comfort", json=CASES[0][1]))
    print("\nOpenAPI fragment of the careful Reading schema:")
    with TestClient(careful_app()) as c:
        print(" ", json.dumps(c.get("/openapi.json").json()["components"]["schemas"]["Reading"]["properties"]
                              ["humidity_pct"]))


if __name__ == "__main__":
    main()
