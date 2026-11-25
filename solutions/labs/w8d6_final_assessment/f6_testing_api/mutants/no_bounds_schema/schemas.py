from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    tier: Literal["starter", "business", "enterprise"]
    tenure_days: int
    shipments_30d: int
    monthly_fee: float
    avg_parcel_kg: Optional[float] = None
