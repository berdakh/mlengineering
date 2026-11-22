"""Prediction API that serves whatever the registry's ``current`` pointer names. Given to you.

    create_app(registry_root, name, serving_columns, token_env="FLOWGUARD_ADMIN_TOKEN") -> FastAPI

* At startup (lifespan) the app loads ``resolve(registry_root, name, "current")``. If that fails it
  still starts, ``/readyz`` answers 503 and ``/predict`` answers 503.
* ``POST /predict`` takes ``{"run_id": str, "datetime": [...], "<sensor>": [...], ...}`` with only
  columns from ``serving_columns`` (the contract with the plant gateway) and returns
  ``flowguard.serving.respond`` for the loaded model. Malformed input answers 422.
* ``POST /admin/reload`` re-reads the ``current`` pointer and swaps the model in memory. It is
  protected by a shared token read from the environment variable ``token_env`` at request time:
  unset -> 403 (reload disabled), wrong or missing ``X-Admin-Token`` header -> 401. If the new bundle
  fails to load, the old model keeps serving and the endpoint answers 409.
  The token is never stored in the repository; set it in the shell that starts the server.
"""
from __future__ import annotations

import hmac
import os
import threading
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from flowguard.registry import BundleError, RegistryError, load_bundle, resolve
from flowguard.serving import respond


def create_app(registry_root, name: str, serving_columns, token_env: str = "FLOWGUARD_ADMIN_TOKEN") -> FastAPI:
    allowed = set(serving_columns) | {"run_id"}
    lock = threading.Lock()

    def load_current():
        model, _doc = load_bundle(resolve(registry_root, name, "current"))
        missing = set(model.required_columns) - set(serving_columns)
        if missing:
            raise BundleError(f"model needs columns the gateway does not send: {sorted(missing)}")
        return model

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.model, app.state.load_error = load_current(), None
        except (BundleError, RegistryError) as exc:
            app.state.model, app.state.load_error = None, str(exc)
        yield

    app = FastAPI(title="flowguard", lifespan=lifespan)

    @app.get("/healthz")
    def healthz():
        return {"status": "alive"}

    @app.get("/readyz")
    def readyz(request: Request):
        if request.app.state.model is None:
            return JSONResponse(status_code=503, content={"ready": False, "error": request.app.state.load_error})
        return {"ready": True, "model_version": request.app.state.model.label}

    @app.get("/version")
    def version(request: Request):
        model = request.app.state.model
        return {"model_version": None if model is None else model.label}

    @app.post("/predict")
    def predict(payload: dict, request: Request):
        model = request.app.state.model
        if model is None:
            raise HTTPException(status_code=503, detail="no model loaded")
        extra = set(payload) - allowed
        if extra:
            raise HTTPException(status_code=422, detail=f"unexpected fields {sorted(extra)}")
        missing = [c for c in model.required_columns if c not in payload]
        if missing:
            raise HTTPException(status_code=422, detail=f"missing fields {missing}")
        try:
            run = pd.DataFrame({c: payload[c] for c in model.required_columns})
            run["datetime"] = pd.to_datetime(run["datetime"])
            for c in model.sensors:
                run[c] = run[c].astype(float)
            if not np.isfinite(run[list(model.sensors)].to_numpy()).all():
                raise ValueError("sensor values must be finite")
            return respond(model, run)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    @app.post("/admin/reload")
    def reload(request: Request, x_admin_token: str | None = Header(default=None)):
        expected = os.environ.get(token_env)
        if not expected:
            raise HTTPException(status_code=403, detail=f"reload disabled: {token_env} is not set")
        if x_admin_token is None or not hmac.compare_digest(x_admin_token, expected):
            raise HTTPException(status_code=401, detail="invalid admin token")
        with lock:
            previous = request.app.state.model
            try:
                model = load_current()
            except (BundleError, RegistryError) as exc:
                raise HTTPException(status_code=409, detail=f"reload failed, still serving "
                                    f"{None if previous is None else previous.label}: {exc}") from None
            request.app.state.model, request.app.state.load_error = model, None
        return {"model_version": model.label, "previous": None if previous is None else previous.label}

    return app
