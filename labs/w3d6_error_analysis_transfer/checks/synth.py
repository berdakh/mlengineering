"""SYNTHETIC detector output for the checks: hand-built label and flag sequences.

Nothing here resembles SKAB. The frames exist so that every expected value can be worked out by hand.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def experiment(labels, flags, experiment_id="valve1/0", family=None) -> pd.DataFrame:
    """One experiment in the tidy schema subset that error analysis needs, plus label and score."""
    labels = np.asarray(labels, dtype=int)
    flags = np.asarray(flags, dtype=int)
    assert len(labels) == len(flags)
    return pd.DataFrame({
        "experiment_id": experiment_id,
        "family": family or experiment_id.split("/")[0],
        "t": np.arange(len(labels)),
        "datetime": pd.Timestamp("2021-01-01") + pd.to_timedelta(np.arange(len(labels)), unit="s"),
        "anomaly": labels,
        "score": flags.astype(float),      # 1.0 = flagged at threshold 0.5
    })


def stack(*frames: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(frames, ignore_index=True)


def seq(*parts) -> list[int]:
    """seq((0, 5), (1, 3)) -> [0,0,0,0,0,1,1,1]"""
    out: list[int] = []
    for value, count in parts:
        out += [value] * count
    return out


def call(fn, tidy: pd.DataFrame, **kwargs):
    return fn(tidy["score"].to_numpy(), tidy["anomaly"].to_numpy(), 0.5, tidy, **kwargs)
