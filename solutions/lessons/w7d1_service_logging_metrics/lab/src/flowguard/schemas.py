"""Request and response schemas of the prediction API. REFERENCE SOLUTION (w5d4)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_SAMPLES = 5000            # one SKAB run has 745-1,327 rows; a full hour at 1 Hz is 3,600
MACHINE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,63}$"

# Sanity limits: physically plausible for the testbed, much wider than the training data
# (see the data dictionary in project/README.md and the lesson). They reject broken inputs
# (unit errors, sentinel values such as -9999, sign errors), not unusual ones: deciding what is
# unusual is the detector's job, and distribution checks belong to monitoring (week 7).
SENSOR_LIMITS: dict[str, tuple[float, float]] = {
    "accelerometer1_rms": (0.0, 10.0),      # g
    "accelerometer2_rms": (0.0, 10.0),      # g
    "current": (0.0, 50.0),                 # A
    "pressure": (-5.0, 20.0),               # bar
    "temperature": (-40.0, 200.0),          # deg C, motor body
    "thermocouple": (-40.0, 200.0),         # deg C, fluid
    "voltage": (0.0, 500.0),                # V
    "flow_rate": (0.0, 500.0),              # L/min
}


def _sensor(name: str, unit: str):
    lo, hi = SENSOR_LIMITS[name]
    return Field(ge=lo, le=hi, allow_inf_nan=False, description=f"{name} in {unit}, finite, in [{lo}, {hi}]")


class Sample(BaseModel):
    """One reading of the eight testbed sensors."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    accelerometer1_rms: float = _sensor("accelerometer1_rms", "g")
    accelerometer2_rms: float = _sensor("accelerometer2_rms", "g")
    current: float = _sensor("current", "A")
    pressure: float = _sensor("pressure", "bar")
    temperature: float = _sensor("temperature", "deg C")
    thermocouple: float = _sensor("thermocouple", "deg C")
    voltage: float = _sensor("voltage", "V")
    flow_rate: float = _sensor("flow_rate", "L/min")


class PredictRequest(BaseModel):
    """A run of one machine from the start of monitoring, in time order."""

    model_config = ConfigDict(extra="forbid")

    machine_id: str = Field(pattern=MACHINE_ID_PATTERN, description="1-64 characters: letters, digits, _ . / -")
    samples: list[Sample] = Field(min_length=1, max_length=MAX_SAMPLES)


class SampleResult(BaseModel):
    timestamp: datetime
    score: float | None
    status: Literal["warming_up", "ok"]
    exceeds_threshold: bool | None


class PredictResponse(BaseModel):
    request_id: str
    model_version: str
    machine_id: str
    threshold: float
    n_samples: int
    results: list[SampleResult]


class ErrorInfo(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    error: ErrorInfo
