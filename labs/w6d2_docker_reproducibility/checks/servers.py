"""Real HTTP servers for grading smoke_test.py: uvicorn in a background thread on 127.0.0.1.

Each variant is a plausible state of a freshly started container:
    good           the reference service with the shipped bundle
    slow_start     /readyz answers 503 for the first few seconds (model still loading)
    never_ready    no model at all: /readyz is 503 forever
    other_model    a different model (version flowguard-z-1.1.0-candidate, n_burn 50)
    wrong_scores   claims version flowguard-z-1.0.0 but computes different scores (n_burn 101)
"""
from __future__ import annotations

import contextlib
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn

HERE = Path(__file__).resolve().parent
SERVICE = HERE / "service"
sys.path.insert(0, str(SERVICE / "src"))

from flowguard.api import create_app  # noqa: E402
from flowguard.bundle import save_bundle  # noqa: E402
from flowguard.inference import Detector  # noqa: E402

BUNDLE = SERVICE / "models" / "flowguard-z" / "1.0.0"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DelayedReady:
    """ASGI wrapper: /readyz answers 503 until `delay` seconds after the server started."""

    def __init__(self, app, delay: float):
        self.app, self.delay, self.t0 = app, delay, None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            self.t0 = time.monotonic()
            return await self.app(scope, receive, send)
        if scope["type"] == "http" and time.monotonic() - (self.t0 or 0) < self.delay:
            body = json.dumps({"error": {"code": "not_ready", "message": "loading"}}).encode()
            await send({"type": "http.response.start", "status": 503,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})
            return
        return await self.app(scope, receive, send)


def _variant_app(kind: str, tmp: Path):
    if kind == "good":
        return create_app(BUNDLE)
    if kind == "slow_start":
        return DelayedReady(create_app(BUNDLE), delay=3.0)
    if kind == "never_ready":
        return create_app(tmp / "no-such-model")
    if kind == "other_model":
        save_bundle(Detector(n_burn=50, version="flowguard-z-1.1.0-candidate"), tmp / "other")
        return create_app(tmp / "other")
    if kind == "wrong_scores":
        save_bundle(Detector(n_burn=101, version="flowguard-z-1.0.0"), tmp / "wrong")
        return create_app(tmp / "wrong")
    raise ValueError(kind)


@contextlib.contextmanager
def serve(kind: str):
    """Yield the base URL of a running server of the given kind; stop it afterwards."""
    with tempfile.TemporaryDirectory() as tmp:
        app = _variant_app(kind, Path(tmp))
        port = free_port()
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error",
                                               lifespan="on"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        if not server.started:
            raise RuntimeError("test server did not start")
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
