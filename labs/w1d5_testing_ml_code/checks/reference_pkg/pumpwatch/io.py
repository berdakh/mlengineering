"""Loading and validating raw window data."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("unit_id", "window_id", "sample", "vibration", "temperature_c", "label")


def load_windows(path: str | Path) -> pd.DataFrame:
    """Read the long-format CSV (one row per sample) and check its columns.

    Raises FileNotFoundError if the file is missing and ValueError if a required
    column is absent, so that failures happen here rather than deep in feature code.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"data file not found: {path}")
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    return df
