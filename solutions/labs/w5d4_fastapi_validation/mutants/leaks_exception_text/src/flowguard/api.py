"""HTTP API for the flowguard detector. REFERENCE SOLUTION (w5d4)."""
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
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from flowguard import __version__
from flowguard.bundle import BundleError, load_bundle
from flowguard.data import SENSOR_COLUMNS
from flowguard.schemas import ErrorResponse, PredictRequest, PredictResponse, SampleResult

API_VERSION = "1"
REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_OK = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
logger = logging.getLogger("flowguard.api")


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


def create_app(model_dir: str | Path | None) -> FastAPI:
    """Build the app. The model is loaded once, at startup; a failed load leaves the app running
    but not ready (``/readyz`` and ``/predict`` answer 503)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.detector, app.state.model_info, app.state.load_error = None, None, None
        try:
            app.state.detector, app.state.model_info = load_bundle(model_dir)
            logger.info("model loaded: %s from %s", app.state.detector.version, model_dir)
        except BundleError as exc:
            app.state.load_error = str(exc)
            logger.error("model not loaded: %s", exc)
        yield

    app = FastAPI(title="flowguard", version=__version__, lifespan=lifespan,
                  description="Fault scores for the SKAB testbed (educational prototype, not for real plants).",
                  responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
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
        logger.exception("unhandled error (request_id=%s)", _request_id(request))
        return _error(request, 500, "internal_error", f"internal error: {exc!r}")

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

    @app.post("/predict", response_model=PredictResponse)
    def predict(body: PredictRequest, request: Request) -> PredictResponse:
        detector = require_detector(request)
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
        return PredictResponse(request_id=_request_id(request), model_version=detector.version,
                               machine_id=body.machine_id, threshold=detector.threshold,
                               n_samples=len(results), results=results)

    return app


def create_app_from_env() -> FastAPI:
    """Factory for ``uvicorn --factory flowguard.api:create_app_from_env`` (reads FLOWGUARD_MODEL_DIR)."""
    return create_app(os.environ.get("FLOWGUARD_MODEL_DIR"))
