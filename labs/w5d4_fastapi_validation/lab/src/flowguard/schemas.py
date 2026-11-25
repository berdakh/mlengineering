"""Request and response schemas of the prediction API. YOU COMPLETE THIS MODULE (w5d4, task 1).

The classes and field names below are the contract the API and the checks rely on. What is missing are
the CONSTRAINTS. Add them with pydantic v2 (``Field``, ``ConfigDict``):

* ``Sample``: no unknown fields (``extra="forbid"``); every sensor value a finite float
  (``allow_inf_nan=False``) inside ``SENSOR_LIMITS[name]`` (inclusive).
* ``PredictRequest``: no unknown fields; ``machine_id`` matches ``MACHINE_ID_PATTERN``; ``samples`` has
  between 1 and ``MAX_SAMPLES`` items.
* The response models need no constraints: the server builds them.

The limits are sanity limits for a broken or mis-scaled input, not the training distribution.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

MAX_SAMPLES = 5000
MACHINE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,63}$"
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


class Sample(BaseModel):
    """One reading of the eight testbed sensors. TODO: constraints."""

    timestamp: datetime
    accelerometer1_rms: float
    accelerometer2_rms: float
    current: float
    pressure: float
    temperature: float
    thermocouple: float
    voltage: float
    flow_rate: float


class PredictRequest(BaseModel):
    """A run of one machine from the start of monitoring, in time order. TODO: constraints."""

    machine_id: str
    samples: list[Sample]


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
