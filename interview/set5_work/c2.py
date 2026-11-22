"""Interview set 5, prompt C2. Implement create_app; keep the names. See interview/set5_system_design.md."""
from typing import Callable, Optional

from fastapi import FastAPI

MODEL_VERSION = "bnpl-risk-0.1.0"
Model = Callable[[float, int, int], float]


def create_app(model: Optional[Model] = None) -> FastAPI:
    raise NotImplementedError
