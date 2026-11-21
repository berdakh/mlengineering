"""Per-window signal features. Pure functions: arrays in, numbers out."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = ("rms", "line_length", "p2p", "bp_low", "bp_high", "ratio", "temp")
LOW_BAND_HZ = (10.0, 40.0)
HIGH_BAND_HZ = (70.0, 110.0)


def fill_gaps(x: np.ndarray) -> np.ndarray:
    """Linearly interpolate NaNs; edge NaNs take the nearest valid value."""
    return pd.Series(np.asarray(x, dtype=float)).interpolate(limit_direction="both").to_numpy()


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x))))


def line_length(x: np.ndarray) -> float:
    return float(np.sum(np.abs(np.diff(x))))


def peak_to_peak(x: np.ndarray) -> float:
    return float(np.max(x) - np.min(x))


def band_power(x: np.ndarray, fs: float, low_hz: float, high_hz: float) -> float:
    """Power of ``x`` in [low_hz, high_hz) from a one-sided periodogram.

    The mean is removed first. Summed over [0, fs/2] the result equals the
    variance of ``x`` (Parseval), which is what the unit tests rely on.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    spectrum = np.fft.rfft(x - x.mean())
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    psd = np.abs(spectrum) ** 2 / (fs * n)
    psd[1:-1] *= 2.0  # fold negative frequencies into the one-sided estimate
    in_band = (freqs >= low_hz) & (freqs < high_hz)
    return float(np.sum(psd[in_band]) * (freqs[1] - freqs[0]))


def window_features(x: np.ndarray, fs: float) -> dict[str, float]:
    """All signal features for one window (NaN gaps are filled first)."""
    x = fill_gaps(x)
    bp_low = band_power(x, fs, *LOW_BAND_HZ)
    bp_high = band_power(x, fs, *HIGH_BAND_HZ)
    return {
        "rms": rms(x),
        "line_length": line_length(x),
        "p2p": peak_to_peak(x),
        "bp_low": bp_low,
        "bp_high": bp_high,
        "ratio": bp_high / bp_low,
    }


def build_feature_table(df: pd.DataFrame, fs: float) -> pd.DataFrame:
    """One row per (unit_id, window_id) with features, temperature and label."""
    n_missing = int(df["vibration"].isna().sum())
    if n_missing:
        logger.warning("interpolating missing samples n_missing=%d n_total=%d", n_missing, len(df))
    rows = []
    for (unit_id, window_id), g in df.groupby(["unit_id", "window_id"], sort=False):
        g = g.sort_values("sample")
        row = {"unit_id": unit_id, "window_id": int(window_id)}
        row.update(window_features(g["vibration"].to_numpy(), fs))
        row["temp"] = float(g["temperature_c"].iloc[0])
        row["label"] = int(g["label"].iloc[0])
        rows.append(row)
    table = pd.DataFrame(rows)
    logger.info("built features windows=%d positive_rate=%.3f", len(table), table["label"].mean())
    return table
