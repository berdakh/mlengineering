"""HTTP API for the flowguard detector. YOU IMPLEMENT THIS MODULE (w5d4, tasks 2-5).

Contract (the checks test it through ``fastapi.testclient.TestClient``; no network is used)
------------------------------------------------------------------------------------------
``create_app(model_dir) -> FastAPI``
    Must not raise, even if ``model_dir`` is missing or the bundle is corrupt. The model is loaded
    ONCE, at startup, in a ``lifespan`` context manager, with ``flowguard.bundle.load_bundle``. After
    startup ``app.state.detector`` is the loaded ``Detector`` or ``None`` if loading failed.

Every response carries an ``X-Request-ID`` header. If the request sent one matching
``^[A-Za-z0-9._-]{1,64}$`` it is echoed; otherwise a new id is generated (``uuid.uuid4().hex``).

Every error response has the body
``{"error": {"code": str, "message": str, "request_id": str, "details": list | null}}``:

============================  ======  ==================  ===============================================
situation                     status  code                details
============================  ======  ==================  ===============================================
body does not match schema    422     validation_error    one dict per problem: {"loc", "type", "msg"},
                                                          "loc" and "type" exactly as pydantic reports them
timestamps not increasing     400     invalid_sequence    one dict per offending sample, loc ends in
                                                          [..., "samples", i, "timestamp"]
model not loaded              503     not_ready           null
unknown path / wrong method   404/405 not_found /         null
                                      method_not_allowed
any unexpected exception      500     internal_error      null; the message must NOT contain the exception
                                                          text or a traceback (log them server-side)
============================  ======  ==================  ===============================================

Endpoints
    GET  /healthz  -> 200 {"status": "ok"} whenever the process can answer (even without a model).
    GET  /readyz   -> 200 {"status": "ready", "model_version": ...} or 503 not_ready.
    GET  /version  -> 200 {"api_version": "1", "package_version": ..., "model_version": ... or null}.
    POST /predict  body ``PredictRequest`` -> 200 ``PredictResponse``: one result per sample, in order,
        equal to ``detector.score_batch`` of the samples (as a DataFrame with a ``datetime`` column):
        ``score`` null and ``status`` "warming_up" where batch gives NaN, otherwise the score,
        ``status`` "ok" and ``exceeds_threshold = score >= detector.threshold``.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

API_VERSION = "1"
REQUEST_ID_HEADER = "X-Request-ID"


def create_app(model_dir: str | Path | None) -> FastAPI:
    app = FastAPI(title="flowguard")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    # TODO task 2: lifespan that loads the bundle into app.state.detector (None on failure)
    # TODO task 3: request-id middleware, /readyz, /version
    # TODO task 4: POST /predict
    # TODO task 5: exception handlers for the error table above
    return app


def create_app_from_env() -> FastAPI:
    """Factory for ``uvicorn --factory flowguard.api:create_app_from_env`` (reads FLOWGUARD_MODEL_DIR)."""
    return create_app(os.environ.get("FLOWGUARD_MODEL_DIR"))
