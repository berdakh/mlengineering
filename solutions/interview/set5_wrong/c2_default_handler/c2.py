"""WRONG (keeps FastAPI's default 422 handler, which echoes the input: NaN becomes a 500 and data leaks into errors).

Interview set 5, prompt C2.

A checkout risk-scoring endpoint: pydantic v2 request schema with constraints, a domain rule,
readiness, and one error body that never echoes the input.
"""
from typing import Callable, Literal, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

MODEL_VERSION = "bnpl-risk-0.1.0"
Model = Callable[[float, int, int], float]


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    sku: str = Field(min_length=1, max_length=40)
    price: float = Field(gt=0, le=5000)


class ScoreRequest(BaseModel):
    # allow_inf_nan=False: NaN/Infinity are reported as "finite_number", not as a range violation.
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    application_id: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0, le=5000)
    currency: Literal["EUR", "GBP", "USD"]
    customer_age_days: int = Field(ge=0, le=36500)
    items: list[Item] = Field(min_length=1, max_length=50)


class ScoreResponse(BaseModel):
    application_id: str
    score: float
    model_version: str


def _error(status: int, code: str, message: str, details: Optional[list] = None) -> JSONResponse:
    body = {"error": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


def create_app(model: Optional[Model] = None) -> FastAPI:
    """`model(amount, customer_age_days, n_items) -> float`. None means "not loaded"."""
    app = FastAPI(title="checkout risk", version=MODEL_VERSION)
    app.state.model = model

    @app.post("/score", response_model=ScoreResponse)
    def score(req: ScoreRequest):
        # Validation has already run (422 first); readiness and domain rules come next.
        if app.state.model is None:
            return _error(503, "not_ready", "model not loaded")
        total = sum(item.price for item in req.items)
        if abs(total - req.amount) > 0.01:
            return _error(400, "amount_mismatch", "sum of item prices differs from amount")
        value = float(app.state.model(req.amount, req.customer_age_days, len(req.items)))
        return ScoreResponse(application_id=req.application_id, score=value, model_version=MODEL_VERSION)

    return app
