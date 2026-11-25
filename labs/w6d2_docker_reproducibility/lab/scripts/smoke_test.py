"""Smoke-test a running flowguard API - YOUR implementation (w6d2 guided lab).

    python scripts/smoke_test.py --base-url http://127.0.0.1:8000
    python scripts/smoke_test.py --base-url http://127.0.0.1:8000 --request smoke/request.json \
        --expected smoke/expected.json --timeout 60

What it must do (lesson section 4.4):
1. Wait until GET /readyz answers 200, polling for up to --timeout seconds. Connection errors and
   503s while the container starts are normal; keep trying until the deadline.
2. POST the fixture request to /predict.
3. Compare the response with smoke/expected.json: same model_version, same number of results, every
   score equal within a relative --tolerance (None must match None), same exceeds_threshold values.

Exit codes (CI will rely on them):
    0  pass
    1  the service answered, but wrongly (status code, model version, scores)
    2  the service never became ready within the timeout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx  # noqa: F401  (use httpx.Client; it is installed with requirements-dev.txt)

HERE = Path(__file__).resolve().parents[1]
PASS, WRONG, NOT_READY = 0, 1, 2


def wait_until_ready(client, timeout: float, interval: float = 0.5) -> str | None:
    """Poll /readyz until 200. Return None when ready, else a description of the last problem."""
    raise NotImplementedError("TODO: poll /readyz until it answers 200 or the timeout expires")


def compare(body: dict, expected: dict, tolerance: float) -> list[str]:
    """Differences between a /predict response body and the expected fixture (empty list = pass)."""
    raise NotImplementedError("TODO: compare model_version, length, scores (None == None) and flags")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--request", default=str(HERE / "smoke" / "request.json"))
    ap.add_argument("--expected", default=str(HERE / "smoke" / "expected.json"))
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--tolerance", type=float, default=1e-9)
    args = ap.parse_args(argv)
    request = json.loads(Path(args.request).read_text())
    expected = json.loads(Path(args.expected).read_text())
    # TODO: open an httpx.Client(base_url=...), wait until ready (exit 2 if not), POST /predict,
    #       compare, print one PASS/FAIL line, return the exit code.
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
