"""HTTP API for the detector. Contract: labs/w5d5_api_testing/lab/CONTRACT.md.

    uvicorn --factory "flowguard.api:app_from_env"      # reads FLOWGUARD_MODEL_DIR
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from flowguard import __version__
from flowguard.bundle import BundleError, load_bundle

API_SCHEMA = "flowguard-api/1"
MAX_VALUES = 3600          # one hour at 1 Hz per request
MAX_BURN_IN = 3600


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    burn_in: list[FiniteFloat] = Field(min_length=2, max_length=MAX_BURN_IN,
                                 description="Readings from the start of the run, used for calibration.")
    values: list[FiniteFloat] = Field(min_length=1,
                                description="Readings to score, oldest first.")


class PredictResponse(BaseModel):
    model_version: str
    threshold: float
    scores: list[float]
    above_threshold: list[bool]


def create_app(model_dir: str | Path) -> FastAPI:
    """Build the app. The bundle is loaded at startup (lifespan), not at import or construction."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.model = load_bundle(model_dir)
            app.state.load_error = None
        except BundleError as exc:            # start degraded: alive but not ready
            app.state.model = None
            app.state.load_error = str(exc)
        yield
        app.state.model = None

    app = FastAPI(title="flowguard", version=__version__, lifespan=lifespan)
    app.state.model = None
    app.state.load_error = "not started"

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # The default handler echoes the offending input. A NaN in the body then makes the 422
        # response itself unserialisable (500), and a large payload would be echoed back in full.
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    def require_model(request: Request):
        model = request.app.state.model
        if model is None:
            raise HTTPException(status_code=503, detail="model not loaded")
        return model

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz(request: Request):
        model = request.app.state.model
        if model is None:
            return JSONResponse(status_code=503,
                                content={"status": "not ready", "reason": request.app.state.load_error})
        return {"status": "ready", "model_version": model.model_version}

    @app.get("/version")
    def version(request: Request) -> dict:
        model = request.app.state.model
        return {"package_version": __version__, "api_schema": API_SCHEMA,
                "model_version": model.model_version if model is not None else None}

    @app.post("/predict", response_model=PredictResponse)
    def predict(body: PredictRequest, request: Request) -> PredictResponse:
        model = require_model(request)
        if len(body.values) > MAX_VALUES:
            raise HTTPException(status_code=413, detail=f"at most {MAX_VALUES} values per request")
        scores = model.score(body.burn_in, body.values)
        flags = model.above_threshold(scores)
        return PredictResponse(model_version=model.model_version, threshold=model.threshold,
                               scores=[float(s) for s in scores], above_threshold=[bool(f) for f in flags])

    return app


def app_from_env() -> FastAPI:
    return create_app(os.environ.get("FLOWGUARD_MODEL_DIR", "models/current"))
