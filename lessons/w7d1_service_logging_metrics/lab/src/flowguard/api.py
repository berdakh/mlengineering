"""HTTP API for the flowguard detector, with structured logs and metrics. STARTER (w7d1): tasks 3a-3c are marked TODO.

New since w5d4: one ``observability_middleware`` that, for EVERY request (including 404s, 422s and
unhandled 500s), assigns or propagates the request id, counts the request, times it, tracks requests in
flight and writes exactly one JSON access-log line; a ``prediction`` event per scored request; and
``GET /metrics`` in the Prometheus text format.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from flowguard import __version__
from flowguard.bundle import BundleError, load_bundle
from flowguard.observability import (ACCESS_LOGGER, PREDICTION_LOGGER, ServiceMetrics, configure_logging,
                                     log_event, now, summarise_samples)
from flowguard.data import SENSOR_COLUMNS
from flowguard.schemas import ErrorResponse, PredictRequest, PredictResponse, SampleResult

API_VERSION = "1"
REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_OK = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
logger = logging.getLogger("flowguard.api")
access_logger = logging.getLogger(ACCESS_LOGGER)
prediction_logger = logging.getLogger(PREDICTION_LOGGER)
METRICS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


class ApiError(Exception):
    """An expected error with a status code and a stable machine-readable code."""

    def __init__(self, status_code: int, code: str, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.status_code, self.code, self.message, self.details = status_code, code, message, details


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    return rid if rid else "unknown"


def _error(request: Request, status_code: int, code: str, message: str, details=None) -> JSONResponse:
    rid = _request_id(request)
    body = {"error": {"code": code, "message": message, "request_id": rid, "details": details}}
    return JSONResponse(status_code=status_code, content=body, headers={REQUEST_ID_HEADER: rid})


def _route_label(request: Request) -> str:
    """The route TEMPLATE (``/predict``), never the raw path: raw paths are unbounded label values."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


def create_app(model_dir: str | Path | None, metrics: ServiceMetrics | None = None) -> FastAPI:
    """Build the app. The model is loaded once, at startup; a failed load leaves the app running
    but not ready (``/readyz`` and ``/predict`` answer 503). ``metrics`` defaults to a fresh registry
    per app, so tests do not share counters."""
    metrics = metrics or ServiceMetrics()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.detector, app.state.model_info, app.state.load_error = None, None, None
        try:
            app.state.detector, app.state.model_info = load_bundle(model_dir)
            metrics.model_info.set(1, model_version=app.state.detector.version)
            log_event(logger, "model_loaded", model_version=app.state.detector.version, model_dir=str(model_dir))
        except BundleError as exc:
            app.state.load_error = str(exc)
            log_event(logger, "model_load_failed", logging.ERROR, model_dir=str(model_dir), reason=str(exc))
        yield

    app = FastAPI(title="flowguard", version=__version__, lifespan=lifespan,
                  description="Fault scores for the SKAB testbed (educational prototype, not for real plants).",
                  responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})

    app.state.metrics = metrics

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        # This is the w5d4 request-id middleware. TODO w7d1 (task 3a): extend it so that EVERY request
        # (200, 404, 422, 503 and an unhandled exception answered with 500) is counted in
        # metrics.requests (labels method, route, status), timed in metrics.latency (label route),
        # tracked in metrics.in_flight, and produces exactly ONE "access" event on access_logger with
        # request_id, method, route, path, status, duration_ms and model_version.
        # Use _route_label(request) for the route label, now() for timing, log_event(...) for logging.
        # Find out what happens to call_next when the endpoint raises (the lesson, section 2.6).
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request.state.request_id = incoming if _REQUEST_ID_OK.match(incoming) else uuid.uuid4().hex
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return _error(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        details = [{"loc": list(e["loc"]), "type": e["type"], "msg": e["msg"]} for e in exc.errors()]
        return _error(request, 422, "validation_error", "the request does not match the schema", details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        codes = {404: "not_found", 405: "method_not_allowed"}
        return _error(request, exc.status_code, codes.get(exc.status_code, "http_error"), str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.error("unhandled_error", exc_info=exc,
                     extra={"fields": {"request_id": _request_id(request), "error_type": type(exc).__name__}})
        return _error(request, 500, "internal_error",
                      "internal error; quote the request_id when reporting it")

    def require_detector(request: Request):
        detector = request.app.state.detector
        if detector is None:
            raise ApiError(503, "not_ready", "the model is not loaded")
        return detector

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz(request: Request) -> dict:
        detector = require_detector(request)
        return {"status": "ready", "model_version": detector.version}

    @app.get("/version")
    def version(request: Request) -> dict:
        detector = request.app.state.detector
        return {"api_version": API_VERSION, "package_version": __version__,
                "model_version": detector.version if detector else None}

    # TODO w7d1 (task 3b): GET /metrics returning metrics.render() as text with media type
    # METRICS_CONTENT_TYPE, excluded from the OpenAPI schema.

    @app.post("/predict", response_model=PredictResponse)
    def predict(body: PredictRequest, request: Request) -> PredictResponse:
        detector = require_detector(request)
        start = now()
        times = [s.timestamp for s in body.samples]
        if len({t.tzinfo is None for t in times}) > 1:
            raise ApiError(400, "invalid_sequence", "timestamps mix timezone-aware and naive values")
        bad = [i for i in range(1, len(times)) if times[i] <= times[i - 1]]
        if bad:
            details = [{"loc": ["body", "samples", i, "timestamp"], "type": "not_increasing",
                        "msg": "timestamp must be later than the previous sample's"} for i in bad[:20]]
            raise ApiError(400, "invalid_sequence", "samples must be strictly increasing in time", details)
        frame = pd.DataFrame([s.model_dump() for s in body.samples]).rename(columns={"timestamp": "datetime"})
        frame = frame[["datetime", *SENSOR_COLUMNS]]
        scores = detector.score_batch(frame)
        results = []
        for t, score in zip(times, scores):
            if pd.isna(score):
                results.append(SampleResult(timestamp=t, score=None, status="warming_up", exceeds_threshold=None))
            else:
                results.append(SampleResult(timestamp=t, score=float(score), status="ok",
                                            exceeds_threshold=bool(score >= detector.threshold)))
        # TODO w7d1 (task 3c): observe every non-null score in metrics.scores, count samples in
        # metrics.samples (outcome warming_up / below / exceeding), and emit ONE "prediction" event on
        # prediction_logger with request_id, machine_id, model_version, threshold, the
        # summarise_samples(...) fields, n_scored, n_warming_up, n_exceeding, max_score, model_ms
        # (milliseconds since `start`). Log a summary of the input, never the samples.
        return PredictResponse(request_id=_request_id(request), model_version=detector.version,
                               machine_id=body.machine_id, threshold=detector.threshold,
                               n_samples=len(results), results=results)

    return app


def create_app_from_env() -> FastAPI:
    """Factory for ``uvicorn --factory flowguard.api:create_app_from_env``.

    Reads FLOWGUARD_MODEL_DIR, and FLOWGUARD_LOG_FILE (JSON lines appended there; default stdout).
    """
    log_file = os.environ.get("FLOWGUARD_LOG_FILE")
    configure_logging(open(log_file, "a", buffering=1) if log_file else None)
    return create_app(os.environ.get("FLOWGUARD_MODEL_DIR"))
