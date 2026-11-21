"""Shared fixtures: every test builds its own small, deterministic data."""
import numpy as np
import pandas as pd
import pytest

from signals import FS, N, tone


@pytest.fixture
def t() -> np.ndarray:
    return np.arange(N) / FS


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(12345)


@pytest.fixture
def make_frame():
    """Factory for a long-format frame (one row per sample) with a known structure.

    Windows in the second half of each unit's record carry a strong 92 Hz
    component and label 1, so every unit contributes both classes and the
    classes are separable by a very wide margin.
    """
    def _make(n_units: int = 6, n_windows: int = 8, n_samples: int = 64, seed: int = 0) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        frames = []
        for u in range(n_units):
            for w in range(n_windows):
                label = int(w >= n_windows // 2)
                x = tone(24.0, 1.0, n_samples) + 0.05 * rng.standard_normal(n_samples)
                if label:
                    x = x + tone(92.0, 2.0, n_samples)
                frames.append(pd.DataFrame({
                    "unit_id": f"U{u:02d}", "window_id": w, "sample": np.arange(n_samples),
                    "vibration": x, "temperature_c": 40.0 + label, "label": label,
                }))
        return pd.concat(frames, ignore_index=True)
    return _make
