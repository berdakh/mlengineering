"""The response the service returns for one run. Given to you.

``respond(model, run)`` is the single definition of a prediction response, used by the API, by the
shadow runner and by the checks, so "the served response" means one thing everywhere::

    {"model_version": "flowguard-1.0.0",
     "scores": [null, ..., 0.41, 7.9, ...],      # null for burn-in rows
     "alarm_events": [[start_row, end_row_exclusive], ...]}
"""
from __future__ import annotations

import math

import pandas as pd

from flowguard.models import BurnInZ


def respond(model: BurnInZ, run: pd.DataFrame) -> dict:
    scores = model.score_run(run)
    return {"model_version": model.label,
            "scores": [None if math.isnan(s) else float(s) for s in scores],
            "alarm_events": [[int(s), int(e)] for s, e in model.alarm_events(run)]}
