"""Fixtures for the w2d5 challenge checks. Grades <target>/timefeatures.py. SYNTHETIC data only."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w2d5_feature_pipeline"
WINDOWS = (30.0, 120.0)
MAX_GAP = 20.0
FEATURES = [f"{s}_{int(w)}s" for w in WINDOWS for s in ("mean", "std", "count")]


def make_series(series_id: str, n: int, seed: int, gap_after: int | None = None) -> pd.DataFrame:
    """Irregular sampling: intervals between 0.5 s and 9 s, optionally one 300 s outage."""
    rng = np.random.default_rng(seed)
    step = rng.uniform(0.5, 9.0, n).round(3)
    if gap_after is not None:
        step[gap_after + 1] = 300.0
    seconds = np.cumsum(step)
    return pd.DataFrame({
        "series_id": series_id,
        "timestamp": pd.Timestamp("2024-05-01 08:00:00") + pd.to_timedelta(seconds + 50 * seed, unit="s"),
        "value": -18.0 + np.cumsum(rng.normal(0, 0.2, n)),
    })


@pytest.fixture()
def frame() -> pd.DataFrame:
    return pd.concat([make_series("freezer-A", 150, 11), make_series("freezer-B", 140, 12, gap_after=70),
                      make_series("freezer-C", 60, 13)], ignore_index=True)


@pytest.fixture(scope="session")
def compute():
    target = resolve_target(UNIT, "challenge")
    path = target / "timefeatures.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("wb_timefeatures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _compute(df, windows_s=WINDOWS, max_gap_s=MAX_GAP):
        try:
            return module.time_window_features(df, windows_s=windows_s, max_gap_s=max_gap_s)
        except NotImplementedError:
            pytest.fail("time_window_features is not implemented yet", pytrace=False)
    return _compute


def slow_reference(df: pd.DataFrame, windows_s=WINDOWS, max_gap_s=MAX_GAP) -> pd.DataFrame:
    """Row-by-row definition of the contract."""
    out = pd.DataFrame(index=df.index, columns=FEATURES, dtype=float)
    for _, group in df.groupby("series_id"):
        group = group.sort_values("timestamp")
        times = (group["timestamp"] - group["timestamp"].iloc[0]).dt.total_seconds().to_numpy()
        values = group["value"].to_numpy(dtype=float)
        start = 0
        for i in range(len(group)):
            if i > 0 and times[i] - times[i - 1] > max_gap_s:
                start = i
            for w in windows_s:
                inside = [j for j in range(start, i + 1) if times[i] - w < times[j] <= times[i]]
                window = values[inside]
                full = times[i] - times[start] >= w
                out.loc[group.index[i], f"count_{int(w)}s"] = len(window)
                out.loc[group.index[i], f"mean_{int(w)}s"] = window.mean() if full else np.nan
                out.loc[group.index[i], f"std_{int(w)}s"] = window.std(ddof=1) if full and len(window) > 1 else np.nan
    return out


def same(a, b) -> bool:
    return np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=1e-8, atol=1e-8, equal_nan=True)
