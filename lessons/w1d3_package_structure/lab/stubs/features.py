"""Per-window signal features. Pure functions: arrays in, numbers out."""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = ("rms", "line_length", "p2p", "bp_low", "bp_high", "ratio", "temp")


def fill_gaps(x: np.ndarray) -> np.ndarray:
    """Linearly interpolate NaNs; edge NaNs take the nearest valid value."""
    raise NotImplementedError


def rms(x: np.ndarray) -> float:
    raise NotImplementedError


def line_length(x: np.ndarray) -> float:
    raise NotImplementedError


def peak_to_peak(x: np.ndarray) -> float:
    raise NotImplementedError


def band_power(x: np.ndarray, fs: float, low_hz: float, high_hz: float) -> float:
    """Power of x in [low_hz, high_hz) from a one-sided periodogram (mean removed).

    The script computes this twice with copy-pasted code. Write it once.
    """
    raise NotImplementedError


def window_features(x: np.ndarray, fs: float) -> dict[str, float]:
    """rms, line_length, p2p, bp_low (10-40 Hz), bp_high (70-110 Hz), ratio for one window."""
    raise NotImplementedError


def build_feature_table(df: pd.DataFrame, fs: float) -> pd.DataFrame:
    """One row per (unit_id, window_id): unit_id, window_id, the signal features, temp, label."""
    raise NotImplementedError
