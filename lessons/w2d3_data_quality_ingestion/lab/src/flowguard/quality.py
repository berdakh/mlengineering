"""Data-quality checks for the tidy SKAB table.  <-- YOU IMPLEMENT THIS (lab tasks 2-3)

Contract (graded by `python wb.py check w2d3`):

* ``run_checks(tidy)`` returns a list of ``CheckResult``, one per check, with unique names.
  It evaluates every check (no early exit), never raises on bad data, never modifies ``tidy``.
* ``detail`` of a failing result names each offending ``experiment_id`` (and only offending ones).
* Severity ``error``: missing column, missing/unparseable values, labels outside {0, 1},
  duplicate (experiment_id, datetime), rows out of time order.
  Severity ``warning``: sampling gaps, stuck sensors, and anything else you decide to watch.
* Thresholds must come from the data: ordinary jitter (2 s steps) and quantisation plateaus
  (the longest in the real files is 43 samples) are not defects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    severity: str = "error"   # "error" stops the pipeline; "warning" is recorded and ingestion continues

    def to_dict(self) -> dict:
        return asdict(self)


def run_checks(tidy: pd.DataFrame) -> list[CheckResult]:
    raise NotImplementedError("lab task 2: implement the error-severity checks, then task 3: the warnings")
