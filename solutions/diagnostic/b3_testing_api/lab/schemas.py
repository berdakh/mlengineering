"""b3 reference: request validation with pydantic v2."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    # Unknown fields are rejected: a misspelt optional field must not be silently ignored.
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(pattern=r"^C\d{5}$")
    plan: Literal["basic", "standard", "premium"]
    tenure_days: int = Field(ge=0)
    sessions_30d: int = Field(ge=0)
    monthly_price: float = Field(gt=0, le=500)
    avg_session_min: float | None = Field(default=None, ge=0)
