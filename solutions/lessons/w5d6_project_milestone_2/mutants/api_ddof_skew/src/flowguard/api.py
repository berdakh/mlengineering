"""HTTP API (schema flowguard-api/1). Serve with:

    FLOWGUARD_MODEL_DIR=models/current uvicorn --factory flowguard.api:app_from_env --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from flowguard import __version__
from flowguard.bundle import BundleError, load_bundle

API_SCHEMA = "flowguard-api/1"
MAX_VALUES = 3600


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    burn_in: list[FiniteFloat] = Field(min_length=2, max_length=3600)
    values: list[FiniteFloat] = Field(min_length=1)


class PredictResponse(BaseModel):
    model_version: str
    threshold: float
    scores: list[float]
    above_threshold: list[bool]


def create_app(model_dir: str | Path) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.model, app.state.load_error = load_bundle(model_dir), None
        except BundleError as exc:
            app.state.model, app.state.load_error = None, str(exc)
        yield
        app.state.model = None

    app = FastAPI(title="flowguard", version=__version__, lifespan=lifespan)
    app.state.model, app.state.load_error = None, "not started"

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
            return JSONResponse(status_code=503, content={"status": "not ready",
                                                          "reason": request.app.state.load_error})
        return {"status": "ready", "model_version": model.model_version}

    @app.get("/version")
    def version(request: Request) -> dict:
        model = request.app.state.model
        return {"package_version": __version__, "api_schema": API_SCHEMA,
                "model_version": model.model_version if model is not None else None}

    @app.post("/predict", response_model=PredictResponse)
    def predict(body: PredictRequest, request: Request) -> PredictResponse:
        model = request.app.state.model
        if model is None:
            raise HTTPException(status_code=503, detail="model not loaded")
        if len(body.values) > MAX_VALUES:
            raise HTTPException(status_code=413, detail=f"at most {MAX_VALUES} values per request")
        import numpy as np
        burn = np.asarray(body.burn_in, dtype=float)
        scores = np.abs(np.asarray(body.values, dtype=float) - burn.mean()) / burn.std(ddof=1)
        return PredictResponse(model_version=model.model_version, threshold=model.threshold,
                               scores=[float(s) for s in scores],
                               above_threshold=[bool(f) for f in model.above_threshold(scores)])

    return app


def app_from_env() -> FastAPI:
    return create_app(os.environ.get("FLOWGUARD_MODEL_DIR", "models/current"))
