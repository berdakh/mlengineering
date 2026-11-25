"""Lab task 3: flowguard.client.RetryingClient against scripted responses (httpx.MockTransport, fake clock)."""
from __future__ import annotations

import random

import httpx
import pytest


class Script:
    """A MockTransport handler that returns scripted outcomes in order and records every request."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        status, headers = outcome if isinstance(outcome, tuple) else (outcome, {})
        return httpx.Response(status, headers=headers, json={"status": status})


def make(fg, script, max_attempts=4, base=1.0, cap=8.0, seed=0):
    sleeps: list[float] = []
    client = fg["client"].RetryingClient(
        "http://flowguard.test", transport=httpx.MockTransport(script),
        policy=fg["client"].RetryPolicy(max_attempts=max_attempts, base_delay=base, max_delay=cap),
        sleep=sleeps.append, rng=random.Random(seed))
    return client, sleeps


def test_retries_503_then_succeeds(fg):
    script = Script(503, 503, 200)
    client, sleeps = make(fg, script)
    r = client.post_json("/predict", {"x": 1})
    assert r.status_code == 200 and len(script.requests) == 3 and len(sleeps) == 2
    assert 0.0 <= sleeps[0] <= 1.0 and 0.0 <= sleeps[1] <= 2.0, f"full jitter bounds violated: {sleeps}"
    assert [e["status"] for e in client.log] == [503, 503, 200]


@pytest.mark.parametrize("status", [400, 404, 409, 413, 422])
def test_never_retries_client_errors(fg, status):
    script = Script(status, 200)
    client, sleeps = make(fg, script)
    assert client.post_json("/predict", {}).status_code == status
    assert len(script.requests) == 1 and sleeps == []


def test_success_is_not_retried(fg):
    script = Script(200)
    client, sleeps = make(fg, script)
    assert client.post_json("/predict", {}).status_code == 200 and len(script.requests) == 1 and not sleeps


def test_honours_retry_after_on_429(fg):
    script = Script((429, {"Retry-After": "3"}), 200)
    client, sleeps = make(fg, script)
    assert client.post_json("/predict", {}).status_code == 200
    assert sleeps == [3.0]


def test_retry_after_is_capped(fg):
    script = Script((503, {"Retry-After": "120"}), 200)
    client, sleeps = make(fg, script, cap=8.0)
    client.post_json("/predict", {})
    assert sleeps == [8.0]


def test_stops_at_max_attempts_and_returns_last_response(fg):
    script = Script(503)
    client, sleeps = make(fg, script, max_attempts=3)
    r = client.post_json("/predict", {})
    assert r.status_code == 503 and len(script.requests) == 3 and len(sleeps) == 2


def test_transport_errors_are_retried_then_raised(fg):
    req = httpx.Request("POST", "http://flowguard.test/predict")
    script = Script(httpx.ConnectError("refused", request=req))
    client, sleeps = make(fg, script, max_attempts=4)
    with pytest.raises(httpx.TransportError):
        client.post_json("/predict", {})
    assert len(script.requests) == 4 and len(sleeps) == 3


def test_transport_error_then_success(fg):
    req = httpx.Request("POST", "http://flowguard.test/predict")
    script = Script(httpx.ReadTimeout("slow", request=req), 200)
    client, _ = make(fg, script)
    assert client.post_json("/predict", {}).status_code == 200


def test_same_idempotency_key_on_every_attempt(fg):
    script = Script(503, 502, 200)
    client, _ = make(fg, script)
    client.post_json("/predict", {})
    keys = [r.headers.get("Idempotency-Key") for r in script.requests]
    assert keys[0] and len(set(keys)) == 1, f"keys differ between attempts: {keys}"


def test_new_key_per_call_and_caller_key_used(fg):
    script = Script(200)
    client, _ = make(fg, script)
    client.post_json("/predict", {})
    client.post_json("/predict", {})
    client.post_json("/predict", {}, idempotency_key="order-42")
    keys = [r.headers.get("Idempotency-Key") for r in script.requests]
    assert keys[0] != keys[1] and keys[2] == "order-42"


def test_full_jitter_distribution(fg):
    client, _ = make(fg, Script(200), base=1.0, cap=8.0, seed=1)
    first = [client.backoff(0) for _ in range(400)]
    third = [client.backoff(2) for _ in range(400)]
    assert all(0.0 <= d <= 1.0 for d in first) and all(0.0 <= d <= 4.0 for d in third)
    assert 0.35 < sum(first) / len(first) < 0.65, "full jitter on [0, 1] should average about 0.5"
    assert len({round(d, 6) for d in first}) > 300, "delays must be random, not a fixed schedule"
    assert max(client.backoff(10) for _ in range(200)) <= 8.0, "the exponential is capped at max_delay"
