"""Tasks that a sweep can run. GIVEN in this lab; you do not need to edit it.

A task is a function ``task(config: dict) -> dict[str, float]`` that reads everything it needs
from the resolved ``config`` (including ``config["seed"]``) and returns its metrics. It must not
write files: recording is the tracker's job, so the same task can be re-run by ``reproduce``
without touching the run directory.

* ``synthetic``     - SYNTHETIC ridge regression, milliseconds per run; used by the checks.
* ``skab_detector`` - a label-free detector on the REAL SKAB development experiments.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

TASKS: dict[str, Callable[[dict], dict]] = {}


def register(name: str):
    def wrap(fn):
        TASKS[name] = fn
        return fn
    return wrap


def get_task(name: str) -> Callable[[dict], dict]:
    try:
        return TASKS[name]
    except KeyError:
        raise ValueError(f"unknown task {name!r}; known: {sorted(TASKS)}") from None


@register("synthetic")
def synthetic(config: dict) -> dict:
    """SYNTHETIC: y = X w + noise, ridge regression in closed form, R^2 and MSE on the last quarter.

    ``config["seed"]`` draws the data, so different seeds give different (but reproducible) metrics.
    ``config["data"]["fail"] = true`` raises, to simulate a crashing run.
    """
    data, model = config["data"], config["model"]
    if data.get("fail"):
        raise RuntimeError("synthetic task asked to fail (data.fail = true)")
    rng = np.random.default_rng(config["seed"])
    n = int(data.get("n_rows", 200))
    x = rng.normal(size=(n, 5))
    y = x @ np.array([1.0, -2.0, 0.5, 0.0, 0.0]) + rng.normal(scale=float(data.get("noise", 1.0)), size=n)
    cut = (3 * n) // 4
    alpha = float(model["alpha"])
    w = np.linalg.solve(x[:cut].T @ x[:cut] + alpha * np.eye(5), x[:cut].T @ y[:cut])
    residual = y[cut:] - x[cut:] @ w
    mse = float(np.mean(residual ** 2))
    return {"mse": mse, "r2": float(1.0 - mse / np.var(y[cut:]))}


class IsolationForestScorer:
    """Isolation forest on the 8 sensors; fit/score contract of flowguard.baselines."""

    def __init__(self, n_estimators: int = 100, seed: int = 0):
        self.n_estimators, self.seed = n_estimators, seed

    def fit(self, train_tidy):
        from sklearn.ensemble import IsolationForest

        from flowguard.data import SENSOR_COLUMNS
        self.columns_ = list(SENSOR_COLUMNS)
        self.model_ = IsolationForest(n_estimators=self.n_estimators, random_state=self.seed)
        self.model_.fit(train_tidy[self.columns_].to_numpy(dtype=float))
        return self

    def score(self, tidy) -> np.ndarray:
        return -self.model_.score_samples(tidy[self.columns_].to_numpy(dtype=float))


EVAL_FROM_T = 200   # every configuration is scored on the same rows, whatever its burn-in


@register("skab_detector")
def skab_detector(config: dict) -> dict:
    """Label-free detector, per-experiment burn-in calibration, scored on the DEVELOPMENT experiments.

    The test experiments are not touched: a sweep is a selection procedure (w3d3).
    config: data.raw_dir, data.manifest; detector.kind in {"mahalanobis", "iforest"}, detector.burn_in,
    detector.shrinkage (mahalanobis) or detector.n_estimators (iforest); seed.
    """
    from flowguard.baselines import MahalanobisScorer, burn_in_scores
    from flowguard.data import load_raw
    from flowguard.metrics import pr_auc
    from flowguard.splits import dev_experiments, load_splits

    data, det = config["data"], config["detector"]
    burn_in = int(det["burn_in"])
    if burn_in > EVAL_FROM_T:
        raise ValueError(f"burn_in {burn_in} > {EVAL_FROM_T}: the calibration rows would be scored")
    tidy = load_raw(data["raw_dir"])
    frame = tidy[tidy["experiment_id"].isin(dev_experiments(load_splits(data["manifest"])))].reset_index(drop=True)
    if det["kind"] == "mahalanobis":
        def make():
            return MahalanobisScorer(float(det["shrinkage"]))
    elif det["kind"] == "iforest":
        def make():
            return IsolationForestScorer(int(det["n_estimators"]), int(config["seed"]))
    else:
        raise ValueError(f"unknown detector.kind {det['kind']!r}")
    scores = burn_in_scores(make, frame, burn_in)
    rows = frame["t"].to_numpy() >= EVAL_FROM_T
    y = frame["anomaly"].to_numpy()
    per_experiment = [pr_auc(y[rows & (frame["experiment_id"] == e).to_numpy()],
                             scores[rows & (frame["experiment_id"] == e).to_numpy()])
                      for e in frame["experiment_id"].unique()]
    return {"dev_pooled_pr_auc": pr_auc(y[rows], scores[rows]),
            "dev_mean_experiment_pr_auc": float(np.nanmean(per_experiment)),
            "n_rows_scored": int(rows.sum())}
