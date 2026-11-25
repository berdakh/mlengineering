"""Mutant: always the smallest model."""
import numpy as np
import pandas as pd


def choose(trials: pd.DataFrame) -> dict:
    fold_columns = [c for c in trials.columns if c.startswith("fold_")]
    row = trials.sort_values(["n_params", "trial"]).iloc[0]
    return {"trial": int(row["trial"]), "estimate": float(np.mean(row[fold_columns].to_numpy(dtype=float)))}
