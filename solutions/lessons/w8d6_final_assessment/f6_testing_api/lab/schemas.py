"""f6 reference: request validation with pydantic v2."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScoreRequest(BaseModel):
    # Unknown fields are rejected: a misspelt optional field must not be silently ignored.
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(pattern=r"^A\d{5}$")
    tier: Literal["starter", "business", "enterprise"]
    tenure_days: int = Field(ge=0)
    shipments_30d: int = Field(ge=0)
    monthly_fee: float = Field(gt=0, le=1000)
    avg_parcel_kg: float | None = Field(default=None, gt=0, le=70)
