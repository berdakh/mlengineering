"""Version 1 of the public API, as released (schema flowguard-api/1). Scores are dummies: only the
OpenAPI schema matters for the challenge."""
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    burn_in: list[FiniteFloat] = Field(min_length=2, max_length=3600)
    values: list[FiniteFloat] = Field(min_length=1)


class PredictResponse(BaseModel):
    model_version: str
    threshold: float
    scores: list[float]
    above_threshold: list[bool]


def create_app() -> FastAPI:
    app = FastAPI(title="flowguard", version="0.5.0")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/version")
    def version() -> dict:
        return {"package_version": "0.5.0"}

    @app.post("/predict", response_model=PredictResponse)
    def predict(body: PredictRequest) -> PredictResponse:
        n = len(body.values)
        return PredictResponse(model_version="v1", threshold=3.0, scores=[0.0] * n, above_threshold=[False] * n)

    return app
