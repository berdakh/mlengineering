"""Worked example: a tiny delivery-ETA service, tested at the HTTP boundary (not flowguard).

ETA in minutes = distance_km / speed_kmh * 60 + handling_min, where speed_kmh is the median of the
courier's recent speeds and handling_min comes from a JSON config loaded at startup.

    create_app(config_path, buggy_cache=False)

``buggy_cache=True`` adds a realistic defect: the median of the last request is kept on the app
object "to save work" and read back after a short pause, so concurrent requests can be answered
with another request's speed. Used by test_eta_service.py and race_demo.py.
"""
from __future__ import annotations

import json
import statistics
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class EtaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    distance_km: FiniteFloat = Field(gt=0, le=500)
    recent_speeds_kmh: list[FiniteFloat] = Field(min_length=1, max_length=50)


class EtaResponse(BaseModel):
    eta_min: float
    config_version: str


def create_app(config_path: str | Path, buggy_cache: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.config = json.loads(Path(config_path).read_text())
        except (OSError, json.JSONDecodeError):
            app.state.config = None
        yield

    app = FastAPI(lifespan=lifespan)
    app.state.config = None

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]})

    @app.get("/readyz")
    def readyz(request: Request):
        if request.app.state.config is None:
            return JSONResponse(status_code=503, content={"status": "not ready"})
        return {"status": "ready"}

    @app.post("/eta", response_model=EtaResponse)
    def eta(body: EtaRequest, request: Request) -> EtaResponse:
        config = request.app.state.config
        if config is None:
            raise HTTPException(status_code=503, detail="config not loaded")
        speed = statistics.median(body.recent_speeds_kmh)
        if buggy_cache:
            request.app.state.last_speed = speed       # shared by every request in this process
            time.sleep(0.001)                          # any I/O or slow step here widens the window
            speed = request.app.state.last_speed
        if speed <= 0:
            raise HTTPException(status_code=422, detail="median speed must be positive")
        minutes = body.distance_km / speed * 60 + config["handling_min"]
        return EtaResponse(eta_min=round(minutes, 6), config_version=config["version"])

    return app
