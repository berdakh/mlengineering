"""Your selection procedure for the recorded trials (challenge, w3d3).

``trials`` has one row per trial: ``trial`` (id), ``family``, ``n_params``, ``learning_rate`` and the
recorded dev scores ``fold_0`` ... ``fold_4`` (higher is better; the same five folds for every trial).
"""
from __future__ import annotations

import pandas as pd


def choose(trials: pd.DataFrame) -> dict:
    """Return ``{"trial": <id>, "estimate": <expected test score of your choice>}``.

    The estimate must be honest: on average over many such tables it should equal the true score of
    the trial you choose. Must not modify ``trials`` and must not depend on row order.
    """
    raise NotImplementedError
