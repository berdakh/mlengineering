"""Small, seeded, **synthetic** datasets for Week 7 (notebooks 25-27), plus SKAB helpers for notebook 28.

    from mlcourse.datasets_w07 import make_deliveries, make_linear_world
    df = make_deliveries()                 # 6,000 synthetic deliveries, 80 couriers, label `late`
    train, valid, test = split_by_courier(df)
    X_train = to_matrix(train)             # numbers only (regions one-hot encoded)

Nothing here is real data. ``make_deliveries`` imitates a delivery company that wants to predict which
deliveries will arrive late. The label depends on the features through thresholds and interactions (where
tree models shine), and on a hidden per-courier effect (so rows of the same courier are correlated, which
matters for honest uncertainty estimates). ``make_linear_world`` is a dataset whose label really is a
logistic function of its features, so a linear model is enough there.

``skab_split`` reads the project's frozen experiment-level split; the SKAB data itself is downloaded by
``python project/get_skab.py`` (GPL-3.0, never committed to this repository).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REGIONS = ["north", "south", "east", "west"]
DELIVERY_FEATURES = ["distance_km", "weight_kg", "n_items", "hour", "weekend", "rain", "region", "tracking_noise"]
NUMERIC_FEATURES = ["distance_km", "weight_kg", "n_items", "hour", "weekend", "rain", "tracking_noise"]


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def make_deliveries(n: int = 6000, n_couriers: int = 80, seed: int = 0) -> pd.DataFrame:
    """Synthetic deliveries: one row per delivery, label ``late`` (1 = arrived late).

    Columns: delivery_id, courier_id, region, distance_km, weight_kg, n_items, hour, weekend, rain,
    tracking_noise (pure noise: a random number with no relation to the label), late.
    """
    rng = np.random.default_rng(seed)
    courier_skill = rng.normal(0.0, 0.5, n_couriers)          # hidden: never given as a feature
    courier_region = rng.choice(REGIONS, n_couriers, p=[0.3, 0.3, 0.2, 0.2])
    courier = rng.integers(0, n_couriers, n)
    region = courier_region[courier]
    distance = np.round(rng.gamma(2.2, 4.0, n), 1)
    weight = np.round(rng.gamma(2.0, 3.0, n), 1)
    n_items = rng.integers(1, 9, n)
    hour = rng.integers(8, 22, n)
    weekend = (rng.random(n) < 2 / 7).astype(int)
    rain = (rng.random(n) < 0.25).astype(int)
    noise = np.round(rng.random(n), 4)
    logit = (-2.8
             + 2.3 * (distance > 12)                          # a threshold, not a slope
             + 2.0 * rain * (region == "north")               # an interaction
             + 1.5 * ((hour >= 18) & (weekend == 0))          # evening rush on weekdays
             + 0.03 * weight
             + courier_skill[courier])
    late = (rng.random(n) < _sigmoid(logit)).astype(int)
    return pd.DataFrame({
        "delivery_id": np.arange(1, n + 1),
        "courier_id": courier + 1,
        "region": region,
        "distance_km": distance,
        "weight_kg": weight,
        "n_items": n_items,
        "hour": hour,
        "weekend": weekend,
        "rain": rain,
        "tracking_noise": noise,
        "late": late,
    })


def split_by_courier(df: pd.DataFrame, seed: int = 0, valid: float = 0.2, test: float = 0.2):
    """Split deliveries into train / valid / test so that every courier is in exactly one part.

    Rows of one courier are correlated (the hidden courier effect), so a random row split would let the
    model "recognise" couriers it has already seen; splitting by courier measures what we care about:
    performance on couriers the model has never seen.
    """
    couriers = np.sort(df["courier_id"].unique())
    rng = np.random.default_rng(seed)
    rng.shuffle(couriers)
    n_test, n_valid = round(len(couriers) * test), round(len(couriers) * valid)
    test_c, valid_c = set(couriers[:n_test]), set(couriers[n_test:n_test + n_valid])
    part = df["courier_id"].map(lambda c: "test" if c in test_c else "valid" if c in valid_c else "train")
    return (df[part == "train"].reset_index(drop=True), df[part == "valid"].reset_index(drop=True),
            df[part == "test"].reset_index(drop=True))


def to_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """The model inputs as numbers: the numeric features plus one 0/1 column per region (one-hot)."""
    X = df[NUMERIC_FEATURES].astype(float).copy()
    for r in REGIONS:
        X[f"region_{r}"] = (df["region"] == r).astype(float)
    return X


def make_linear_world(n: int = 3000, seed: int = 0) -> pd.DataFrame:
    """Synthetic data whose label really is logistic-linear in x1..x4 (x5 is noise). Label ``y``."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 5))
    logit = 0.3 + 1.2 * X[:, 0] - 0.8 * X[:, 1] + 0.5 * X[:, 2] + 0.3 * X[:, 3]
    y = (rng.random(n) < _sigmoid(logit)).astype(int)
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(1, 6)])
    df["y"] = y
    return df


# ----------------------------------------------------------------------------- SKAB (notebook 28)

SKAB_COLUMNS = {
    "Accelerometer1RMS": "accel1",
    "Accelerometer2RMS": "accel2",
    "Current": "current",
    "Pressure": "pressure",
    "Temperature": "temperature",
    "Thermocouple": "thermocouple",
    "Voltage": "voltage",
    "Volume Flow RateRMS": "flow_rate",
}
SKAB_SENSORS = list(SKAB_COLUMNS.values())
SPLIT_MANIFEST = Path("solutions/labs/w3d1_leakage/lab/splits/v2.json")


def skab_split(repo_root: str | Path = ".") -> dict:
    """The frozen experiment-level split (version v2): {'dev': [...27 ids], 'test': [...7 ids]}."""
    manifest = json.loads((Path(repo_root) / SPLIT_MANIFEST).read_text())
    dev = sorted(e for fold in manifest["dev_folds"] for e in fold)
    return {"dev": dev, "test": sorted(manifest["test"]), "version": manifest["version"]}
