"""Loading and validating raw window data."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("unit_id", "window_id", "sample", "vibration", "temperature_c", "label")


def load_windows(path: str | Path) -> pd.DataFrame:
    """Read the long-format CSV (one row per sample).

    Raise FileNotFoundError if the file does not exist and ValueError (naming the
    columns) if any of REQUIRED_COLUMNS is absent.
    """
    raise NotImplementedError
