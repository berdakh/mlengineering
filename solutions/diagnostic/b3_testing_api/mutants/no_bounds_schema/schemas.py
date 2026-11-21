from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: str
    plan: Literal["basic", "standard", "premium"]
    tenure_days: int
    sessions_30d: int
    monthly_price: float
    avg_session_min: Optional[float] = None
