"""Smoke test against a RUNNING service: is it up, ready, and does /predict answer sensibly?

    python scripts/smoke_test.py --url http://127.0.0.1:8000 [--timeout 30] [--expect-model flowguard-z-1.0.0]

Standard library only, so it runs on a CI runner or a laptop without installing the project.
Exit code 0 = pass, 1 = fail (with the reason on stderr). Sends SYNTHETIC samples.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

SENSORS = {"accelerometer1_rms": 0.21, "accelerometer2_rms": 0.27, "current": 1.9, "pressure": 0.3,
           "temperature": 80.0, "thermocouple": 25.0, "voltage": 230.0, "flow_rate": 32.0}


def call(url: str, body: dict | None = None, timeout: float = 5.0) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def wait_ready(base: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    last = "no answer"
    while time.monotonic() < deadline:
        try:
            status, body = call(f"{base}/readyz", timeout=2.0)
            if status == 200:
                return body
            last = f"/readyz answered {status}"
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            last = repr(exc)
        time.sleep(0.5)
    raise SystemExit(f"FAIL: service not ready after {timeout:.0f} s ({last})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--expect-model", default=None)
    args = ap.parse_args(argv)
    base = args.url.rstrip("/")
    ready = wait_ready(base, args.timeout)
    print(f"ready: model {ready.get('model_version')}")
    if args.expect_model and ready.get("model_version") != args.expect_model:
        print(f"FAIL: expected model {args.expect_model}, got {ready.get('model_version')}", file=sys.stderr)
        return 1
    start = datetime(2026, 3, 1, 10, 0, 0)
    samples = [{"timestamp": (start + timedelta(seconds=i)).isoformat(), **SENSORS} for i in range(150)]
    status, body = call(f"{base}/predict", {"machine_id": "smoke-test", "samples": samples})
    if status != 200:
        print(f"FAIL: /predict answered {status}: {body}", file=sys.stderr)
        return 1
    if body.get("n_samples") != len(samples) or not body.get("model_version"):
        print(f"FAIL: unexpected /predict body: {str(body)[:300]}", file=sys.stderr)
        return 1
    status, _ = call(f"{base}/predict", {"machine_id": "smoke-test", "samples": []})
    if status != 422:
        print(f"FAIL: an empty request should be 422, got {status}", file=sys.stderr)
        return 1
    print(f"PASS: /predict scored {body['n_samples']} samples with {body['model_version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
