"""scripts/smoke_test.py (w6d2): graded by running it against real servers (servers.py)."""
from __future__ import annotations

import subprocess
import sys
import time

import pytest

import servers


def run_smoke(target, base_url, timeout, extra=()):
    script = target / "scripts" / "smoke_test.py"
    if not script.is_file():
        pytest.fail("no scripts/smoke_test.py", pytrace=False)
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(script), "--base-url", base_url, "--timeout", str(timeout),
         "--request", str(target / "smoke" / "request.json"),
         "--expected", str(target / "smoke" / "expected.json"), *extra],
        capture_output=True, text=True, timeout=timeout + 60)
    return proc, time.monotonic() - started


def _no_crash(proc):
    assert "Traceback" not in proc.stderr, "the smoke test crashed instead of reporting: " + proc.stderr[-600:]


def _explain(proc):
    return f"exit {proc.returncode}; stdout: {proc.stdout[-400:]!r}; stderr: {proc.stderr[-600:]!r}"


def test_passes_against_the_correct_service(target):
    with servers.serve("good") as url:
        proc, _ = run_smoke(target, url, timeout=20)
    assert proc.returncode == 0, _explain(proc)


def test_waits_for_a_service_that_is_still_starting(target):
    with servers.serve("slow_start") as url:
        proc, took = run_smoke(target, url, timeout=20)
    assert proc.returncode == 0, ("a container that needs 3 s to become ready must pass: poll /readyz "
                                  "until the timeout instead of failing at the first 503. " + _explain(proc))


def test_reports_not_ready_with_exit_code_2(target):
    with servers.serve("never_ready") as url:
        proc, took = run_smoke(target, url, timeout=3)
    _no_crash(proc)
    assert proc.returncode == 2, "a service whose /readyz never answers 200 must exit 2. " + _explain(proc)
    assert took < 3 + 25, f"took {took:.0f} s with --timeout 3: the timeout is not respected"


def test_reports_unreachable_with_exit_code_2(target):
    proc, took = run_smoke(target, f"http://127.0.0.1:{servers.free_port()}", timeout=2)
    _no_crash(proc)
    assert proc.returncode == 2, "nothing listening must exit 2 (not ready), not crash. " + _explain(proc)
    assert took < 2 + 25


def test_detects_a_different_model(target):
    with servers.serve("other_model") as url:
        proc, _ = run_smoke(target, url, timeout=20)
    _no_crash(proc)
    assert proc.returncode == 1, "a different model_version must exit 1. " + _explain(proc)


def test_detects_wrong_scores_under_the_right_version(target):
    with servers.serve("wrong_scores") as url:
        proc, _ = run_smoke(target, url, timeout=20)
    _no_crash(proc)
    assert proc.returncode == 1, ("the service claims flowguard-z-1.0.0 but returns different scores; "
                                  "checking status and version is not enough. " + _explain(proc))
