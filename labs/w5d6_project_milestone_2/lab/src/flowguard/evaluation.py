"""Evaluation path: the scores the milestone report is built from. Calls the packaged inference."""
from __future__ import annotations

import numpy as np
import pandas as pd

from flowguard.inference import score_experiments
from flowguard.scoring import ZScoreModel


def experiment_scores(model: ZScoreModel, tidy: pd.DataFrame, experiments=None) -> pd.DataFrame:
    """Scores for the given experiments (all if None), joined with their labels."""
    if experiments is not None:
        tidy = tidy[tidy["experiment_id"].isin(set(experiments))]
    scored = score_experiments(model, tidy)
    labels = tidy[["experiment_id", "t", "anomaly"]]
    return scored.merge(labels, on=["experiment_id", "t"], how="left", validate="one_to_one")


def point_summary(scored: pd.DataFrame, n_burn_in: int) -> dict:
    """Point-level counts after the burn-in rows: a quick sanity summary, not the full w3d4 evaluation."""
    s = scored[scored["t"] >= n_burn_in]
    y, flag = s["anomaly"].to_numpy(dtype=int), s["above_threshold"].to_numpy(dtype=bool)
    tp = int(np.sum(flag & (y == 1)))
    return {"rows": int(len(s)), "positives": int(y.sum()), "flagged": int(flag.sum()), "true_positives": tp,
            "precision": tp / max(int(flag.sum()), 1), "recall": tp / max(int(y.sum()), 1)}
