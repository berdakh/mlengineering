"""Service settings: configs/service.toml, overridable by FLOWGUARD_* environment variables. GIVEN.

The fallback envelope and the training support deliberately live HERE, not in the model bundle:
the fallback must still work when the bundle is the thing that failed.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, fields, replace
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    deadline_s: float = 0.5          # per-request budget for the model call
    max_inflight: int = 4            # bulkhead: concurrent model calls; more -> 429
    retry_after_s: int = 1           # Retry-After header on 429
    support_low: float = 0.0         # range of the sensor seen in development data (model-level guard)
    support_high: float = 1.0e9
    envelope_low: float = 0.0        # fallback rule: alarm outside the normal operating envelope
    envelope_high: float = 1.0e9

    def __post_init__(self) -> None:
        if self.deadline_s <= 0 or self.max_inflight < 1 or self.retry_after_s < 0:
            raise ValueError("deadline_s > 0, max_inflight >= 1 and retry_after_s >= 0 are required")
        if not (self.support_low < self.support_high and self.envelope_low < self.envelope_high):
            raise ValueError("support and envelope need low < high")


def load_settings(path: str | Path | None = None) -> Settings:
    settings = Settings()
    if path is not None and Path(path).is_file():
        data = tomllib.loads(Path(path).read_text())
        known = {f.name for f in fields(Settings)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"{path}: unknown settings {sorted(unknown)}")
        settings = replace(settings, **data)
    overrides = {}
    for f in fields(Settings):
        raw = os.environ.get(f"FLOWGUARD_{f.name.upper()}")
        if raw is not None:
            overrides[f.name] = int(raw) if f.type in ("int", int) else float(raw)
    return replace(settings, **overrides) if overrides else settings
