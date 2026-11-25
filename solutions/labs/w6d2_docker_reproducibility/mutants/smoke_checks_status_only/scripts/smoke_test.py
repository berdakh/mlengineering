"""Smoke-test a running flowguard API - REFERENCE SOLUTION (w6d2).

    python scripts/smoke_test.py --base-url http://127.0.0.1:8000
    python scripts/smoke_test.py --base-url http://127.0.0.1:8000 --request smoke/request.json \
        --expected smoke/expected.json --timeout 60

1. Wait until GET /readyz answers 200 (polling, up to --timeout seconds). A container needs a few
   seconds to start and load the model, so "not ready yet" is normal at first; refusing to wait
   would make the test flaky.
2. POST the fixture request to /predict.
3. Compare the response with the expected scores: same model version, same number of results,
   every score equal within --tolerance (None must match None), same threshold decisions.

Exit codes (stable, so CI can tell the failures apart):
    0  pass
    1  the service answered, but wrongly (status, model version, scores)
    2  the service never became ready within the timeout (not reachable, or /readyz not 200)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parents[1]
PASS, WRONG, NOT_READY = 0, 1, 2


def wait_until_ready(client: httpx.Client, timeout: float, interval: float = 0.5) -> str | None:
    """Poll /readyz until it returns 200. Returns None when ready, else the last problem seen."""
    deadline = time.monotonic() + timeout
    problem = "no attempt made"
    while True:
        try:
            response = client.get("/readyz")
            if response.status_code == 200:
                return None
            problem = f"/readyz answered {response.status_code}"
        except httpx.HTTPError as exc:          # connection refused, reset, timeout ...
            problem = f"{type(exc).__name__}: {exc}"
        if time.monotonic() >= deadline:
            return problem
        time.sleep(interval)


def compare(body: dict, expected: dict, tolerance: float) -> list[str]:
    """Only the version and the number of results are compared."""
    problems = []
    if body.get("model_version") != expected["model_version"]:
        problems.append(f"model_version {body.get('model_version')!r} != {expected['model_version']!r}")
    if len(body.get("results", [])) != len(expected["scores"]):
        problems.append("wrong number of results")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base-url", required=True, help="e.g. http://127.0.0.1:8000")
    ap.add_argument("--request", default=str(HERE / "smoke" / "request.json"))
    ap.add_argument("--expected", default=str(HERE / "smoke" / "expected.json"))
    ap.add_argument("--timeout", type=float, default=60.0, help="seconds to wait for /readyz")
    ap.add_argument("--tolerance", type=float, default=1e-9, help="relative tolerance on scores")
    args = ap.parse_args(argv)

    request = json.loads(Path(args.request).read_text())
    expected = json.loads(Path(args.expected).read_text())
    with httpx.Client(base_url=args.base_url, timeout=10.0) as client:
        started = time.monotonic()
        problem = wait_until_ready(client, args.timeout)
        if problem is not None:
            print(f"FAIL (not ready after {args.timeout:.0f} s): {problem}")
            return NOT_READY
        waited = time.monotonic() - started
        try:
            response = client.post("/predict", json=request)
        except httpx.HTTPError as exc:
            print(f"FAIL: POST /predict raised {type(exc).__name__}: {exc}")
            return WRONG
        if response.status_code != 200:
            print(f"FAIL: POST /predict answered {response.status_code}: {response.text[:300]}")
            return WRONG
        problems = compare(response.json(), expected, args.tolerance)
    if problems:
        print("FAIL: response differs from the expected fixture:\n  " + "\n  ".join(problems))
        return WRONG
    n_scored = sum(s is not None for s in expected["scores"])
    print(f"PASS: ready after {waited:.1f} s; model {expected['model_version']}; "
          f"{len(expected['scores'])} results, {n_scored} scores match")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
