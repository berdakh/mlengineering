"""w4d2 challenge: unsupervised vs supervised fraud scoring under label scarcity. See README.md.

Implement ``run``. Keep the signature; the checks call it on freshly generated data.
"""
from __future__ import annotations

import pandas as pd


def run(train: pd.DataFrame, seed: int = 0) -> dict:
    """Return {"choice": "iforest" | "gbt",
               "estimates": {"iforest": float, "gbt": float},   # your honest estimate of test AP
               "model": object with .score(df) -> array, fitted on ``train``, higher = more likely fraud}

    ``df`` passed to ``model.score`` has the same columns as ``train`` except ``label``.
    """
    raise NotImplementedError
