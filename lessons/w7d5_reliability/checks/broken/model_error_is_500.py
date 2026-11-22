"""BROKEN SERVICE: an exception in the model call escapes as a 500."""
"""HTTP API with reliability guards (schema flowguard-api/2).

    FLOWGUARD_MODEL_DIR=bundle uvicorn --factory flowguard.api:app_from_env --host 127.0.0.1 --port 8000

Behaviour contract (the checks grade exactly this):

* Input that violates the schema -> 422 (validation at the edge; unchanged from w5d4).
* Values outside the training support -> still scored; their indices in ``out_of_support``; counter
  ``flowguard_out_of_support_total`` increases by the number of such values.
* Model unavailable (bundle failed to load), model raises, model returns non-finite scores, or the
  model call misses the deadline -> 200 with ``degraded: true``, ``reason`` one of
  ``model_unavailable | model_error | invalid_scores | deadline``, ``fallback: "envelope-rule"``,
  ``scores: null`` and ``above_threshold`` from the fallback rule; counter
  ``flowguard_degraded_total{reason=...}`` and a ``degraded`` log event with the request id.
* More than ``max_inflight`` model calls in flight -> 429 with a ``Retry-After`` header; counter
  ``flowguard_shed_total``; a ``shed`` log event.
* ``/healthz`` (liveness) is 200 whenever the process can answer, degraded or not.
* ``/readyz`` (readiness) is 200 ``{"status": "ready"}`` with a loaded model and
  503 ``{"status": "degraded", "reason": ..., "fallback": "envelope-rule"}`` without one.
* Every response carries ``X-Request-ID`` (taken from the request header when present).
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from flowguard import __version__
from flowguard.bundle import BundleError, load_bundle
from flowguard.faults import faults_from_env
from flowguard.guards import all_finite, fallback_alarms, out_of_support
from flowguard.obs import Metrics, log_event
from flowguard.settings import Settings, load_settings

API_SCHEMA = "flowguard-api/2"
MAX_VALUES = 3600
FALLBACK = "envelope-rule"


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    burn_in: list[FiniteFloat] = Field(min_length=2, max_length=MAX_VALUES)
    values: list[FiniteFloat] = Field(min_length=1, max_length=MAX_VALUES)


def _score(model, burn_in, values, faults) -> list[float]:
    """The model call, with the injected faults applied. Runs in the bulkhead's worker threads."""
    if "slow_model" in faults:
        time.sleep(float(faults["slow_model"]))
    if "model_error" in faults:
        raise RuntimeError("injected model_error")
    scores = model.score(burn_in, values)
    if "nan_scores" in faults:
        scores = np.full(len(values), np.nan)
    return [float(s) for s in scores]


def create_app(model_dir: str | Path, settings: Settings | None = None,
               faults: dict | None = None) -> FastAPI:
    settings = settings or load_settings(os.environ.get("FLOWGUARD_SETTINGS"))
    faults = faults_from_env() if faults is None else dict(faults)
    metrics = Metrics()
    executor = ThreadPoolExecutor(max_workers=settings.max_inflight, thread_name_prefix="model")
    slots = threading.BoundedSemaphore(settings.max_inflight)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            if "bundle_corrupt" in faults:
                raise BundleError("injected bundle_corrupt")
            app.state.model, app.state.load_error = load_bundle(model_dir), None
        except BundleError as exc:
            app.state.model, app.state.load_error = None, str(exc)
            log_event("model_load_failed", reason=str(exc))
        yield
        executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(title="flowguard", version=__version__, lifespan=lifespan)
    app.state.model, app.state.load_error = None, "not started"
    app.state.metrics, app.state.settings, app.state.faults = metrics, settings, faults

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        metrics.inc("flowguard_requests_total", path=request.url.path, status=str(response.status_code))
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]})

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz(request: Request):
        model = request.app.state.model
        if model is None:
            return JSONResponse(status_code=503, content={
                "status": "degraded", "reason": request.app.state.load_error, "fallback": FALLBACK})
        return {"status": "ready", "model_version": model.model_version}

    @app.get("/version")
    def version(request: Request) -> dict:
        model = request.app.state.model
        return {"package_version": __version__, "api_schema": API_SCHEMA,
                "model_version": model.model_version if model is not None else None}

    @app.get("/metrics")
    def metrics_endpoint() -> PlainTextResponse:
        return PlainTextResponse(metrics.render())

    @app.post("/predict")
    def predict(body: PredictRequest, request: Request):
        rid = request.state.request_id
        model = request.app.state.model
        oos = out_of_support(body.values, settings.support_low, settings.support_high)
        if oos:
            metrics.inc("flowguard_out_of_support_total", amount=len(oos))
            log_event("out_of_support", request_id=rid, count=len(oos))

        def degraded(reason: str) -> dict:
            metrics.inc("flowguard_degraded_total", reason=reason)
            log_event("degraded", request_id=rid, reason=reason)
            return {"model_version": model.model_version if model is not None else None,
                    "degraded": True, "reason": reason, "fallback": FALLBACK, "scores": None,
                    "above_threshold": fallback_alarms(body.values, settings.envelope_low, settings.envelope_high),
                    "out_of_support": oos, "request_id": rid}

        if model is None:
            return degraded("model_unavailable")
        if not slots.acquire(blocking=False):
            metrics.inc("flowguard_shed_total")
            log_event("shed", request_id=rid, max_inflight=settings.max_inflight)
            return JSONResponse(status_code=429, headers={"Retry-After": str(settings.retry_after_s)},
                                content={"detail": "too many requests in flight; retry later", "request_id": rid})
        future = executor.submit(_score, model, body.burn_in, body.values, faults)
        future.add_done_callback(lambda _f: slots.release())     # the slot is held until the work ends
        try:
            scores = future.result(timeout=settings.deadline_s)
        except FutureTimeout:
            return degraded("deadline")
        if not all_finite(scores):
            return degraded("invalid_scores")
        return {"model_version": model.model_version, "degraded": False, "reason": None, "fallback": None,
                "threshold": model.threshold, "scores": scores,
                "above_threshold": [bool(s >= model.threshold) for s in scores],
                "out_of_support": oos, "request_id": rid}

    return app


def app_from_env() -> FastAPI:
    return create_app(os.environ.get("FLOWGUARD_MODEL_DIR", "bundle"))
