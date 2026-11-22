"""A retrying HTTP client for the flowguard API (the learner implements it in the lab).

Contract (graded by the checks):

* Every attempt of one logical call sends the SAME ``Idempotency-Key`` header (the caller's key, or a
  new uuid4 hex when none is given). Different calls get different keys.
* Retry on 429, 502, 503, 504 and on transport errors (``httpx.TransportError``: connection refused,
  read timeout, ...). Never retry any other status: a 400/404/422 will fail the same way again.
* At most ``policy.max_attempts`` attempts in total.
* Delay before retry number k (k = 0 for the first retry): if the response has a ``Retry-After`` header
  in seconds, sleep exactly that (capped at ``policy.max_delay``); otherwise "full jitter":
  ``uniform(0, min(policy.max_delay, policy.base_delay * 2**k))``.
* When attempts run out: return the last response if there was one, else raise the last transport error.
* ``self.log`` gets one dict per attempt: {"attempt", "status" (or None), "error" (or None), "delay"}.
"""
from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass

import httpx

RETRY_STATUSES = frozenset({429, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.2
    max_delay: float = 5.0


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None          # an HTTP date: not used by this service; fall back to jitter


class RetryingClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", *, transport: httpx.BaseTransport | None = None,
                 policy: RetryPolicy | None = None, sleep=time.sleep, rng: random.Random | None = None,
                 timeout: float = 2.0) -> None:
        self.policy = policy or RetryPolicy()
        self.sleep = sleep
        self.rng = rng or random.Random()
        self.log: list[dict] = []
        self._http = httpx.Client(base_url=base_url, transport=transport, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "RetryingClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def backoff(self, retry_index: int) -> float:
        """Full-jitter delay before retry number retry_index (0 for the first retry). Lab task 3."""
        raise NotImplementedError("lab task 3")

    def post_json(self, path: str, payload: dict, idempotency_key: str | None = None) -> httpx.Response:
        """POST payload as JSON with retries, following the contract in the module docstring. Lab task 3.

        Use self._http.post(path, json=payload, headers={"Idempotency-Key": key}) for each attempt,
        self.sleep(delay) to wait (never time.sleep directly: the checks pass a fake clock), and
        append one dict per attempt to self.log.
        """
        raise NotImplementedError("lab task 3")
