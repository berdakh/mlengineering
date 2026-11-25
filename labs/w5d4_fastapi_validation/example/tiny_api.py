"""Worked example (w5d4): a tiny, unrelated API built two ways. SYNTHETIC; no model file needed.

A "room comfort" service: POST a list of (temperature, humidity) readings, get a comfort index per
reading. The "model" is a dict of coefficients loaded at startup, standing in for a model bundle.

``naive_app()``   what most first versions look like: types only, FastAPI's default errors,
                  coefficients loaded per request, an exception text returned to the client.
``careful_app()`` the same endpoint with the patterns of lesson w5d4: constraints, extra="forbid",
                  lifespan loading, one error body for every failure, no leaked internals.

Run ``demo_requests.py`` to see the difference.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

COEFFS = Path(__file__).with_name("comfort_coeffs.json")


def comfort(t: float, h: float, c: dict) -> float:
    return round(100 - c["a"] * abs(t - c["t_opt"]) - c["b"] * abs(h - c["h_opt"]), 3)


# ------------------------------------------------------------------------------------------ naive
class NaiveReading(BaseModel):
    temperature_c: float
    humidity_pct: float


def naive_app() -> FastAPI:
    app = FastAPI()

    @app.post("/comfort")
    def score(readings: list[NaiveReading]):
        c = json.loads(COEFFS.read_text())                    # loaded on every request
        try:
            return {"comfort": [comfort(r.temperature_c, r.humidity_pct, c) for r in readings]}
        except Exception as exc:                              # "helpful" debugging output
            return JSONResponse(status_code=500, content={"error": repr(exc)})

    return app


# ---------------------------------------------------------------------------------------- careful
class Reading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    temperature_c: float = Field(ge=-30, le=60, allow_inf_nan=False)
    humidity_pct: float = Field(ge=0, le=100, allow_inf_nan=False)


class ComfortRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    readings: list[Reading] = Field(min_length=1, max_length=1000)


def careful_app(coeffs_path: Path = COEFFS) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.coeffs = json.loads(coeffs_path.read_text())   # once, at startup
        yield

    app = FastAPI(lifespan=lifespan)

    def error(status: int, code: str, message: str, details=None) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message,
                                                                   "details": details}})

    @app.exception_handler(RequestValidationError)
    async def on_invalid(request: Request, exc: RequestValidationError):
        return error(422, "validation_error", "request does not match the schema",
                     [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()])

    @app.exception_handler(Exception)
    async def on_crash(request: Request, exc: Exception):
        return error(500, "internal_error", "internal error")    # details go to the log, not the client

    @app.post("/comfort")
    def score(body: ComfortRequest, request: Request):
        c = request.app.state.coeffs
        return {"comfort": [comfort(r.temperature_c, r.humidity_pct, c) for r in body.readings]}

    return app
