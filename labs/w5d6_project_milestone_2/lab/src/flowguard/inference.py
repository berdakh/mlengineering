"""Batch inference over a tidy table: one score per row, burn-in taken per experiment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from flowguard.scoring import ZScoreModel


def score_experiments(model: ZScoreModel, tidy: pd.DataFrame) -> pd.DataFrame:
    """Columns experiment_id, t, score, above_threshold, in the order of ``tidy`` sorted by (experiment_id, t).

    Each experiment is calibrated on its own first ``model.n_burn_in`` rows. Those rows are scored
    in-sample and are excluded from evaluation (w2d6); they are still returned, flagged by ``t``.
    """
    parts = []
    for experiment_id, group in tidy.groupby("experiment_id", sort=True):
        group = group.sort_values("t", kind="stable")
        x = group[model.sensor].to_numpy(dtype=float)
        if len(x) <= model.n_burn_in:
            raise ValueError(f"{experiment_id}: {len(x)} rows, fewer than burn-in {model.n_burn_in} + 1")
        scores = model.score(x[: model.n_burn_in], x)
        parts.append(pd.DataFrame({"experiment_id": experiment_id, "t": group["t"].to_numpy(),
                                   "score": scores, "above_threshold": model.above_threshold(scores)}))
    if not parts:
        return pd.DataFrame(columns=["experiment_id", "t", "score", "above_threshold"])
    return pd.concat(parts, ignore_index=True)


def api_requests_for(model: ZScoreModel, tidy: pd.DataFrame, experiment_id: str, max_values: int = 3600) -> list[dict]:
    """/predict request bodies that together score one whole experiment.

    The API accepts at most ``max_values`` values per request, so long recordings are sent in chunks.
    Every chunk carries the same burn-in, so the concatenated scores equal batch scoring.
    """
    x = tidy[tidy["experiment_id"] == experiment_id].sort_values("t")[model.sensor].to_numpy(dtype=float)
    burn = x[: model.n_burn_in].tolist()
    return [{"burn_in": burn, "values": x[i:i + max_values].tolist()} for i in range(0, len(x), max_values)]
