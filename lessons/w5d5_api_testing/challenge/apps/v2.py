"""A proposed version 2. A colleague says it is "fully backwards compatible". Is it?"""
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str = Field(description="Plant site; needed for per-site thresholds.")
    burn_in: list[FiniteFloat] = Field(min_length=2, max_length=600)
    values: list[FiniteFloat] = Field(min_length=1)
    explain: bool = False


class PredictResponse(BaseModel):
    model_version: str
    threshold: float
    score: list[float]
    above_threshold: list[bool]
    latency_ms: float | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="flowguard", version="0.6.0")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/version")
    def version() -> dict:
        return {"package_version": "0.6.0"}

    @app.post("/predict", response_model=PredictResponse)
    def predict(body: PredictRequest) -> PredictResponse:
        n = len(body.values)
        return PredictResponse(model_version="v2", threshold=3.0, score=[0.0] * n, above_threshold=[False] * n)

    @app.get("/sites")
    def sites() -> list[str]:
        return ["plant-a"]

    return app
