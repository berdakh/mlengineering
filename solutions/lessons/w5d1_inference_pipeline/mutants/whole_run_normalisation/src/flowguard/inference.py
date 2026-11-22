"""One inference object for the shipped detector, used by offline evaluation AND by serving.

The detector chosen in w4d5 is the flow-rate |z| score: at the start of every run, the first
``n_burn`` rows calibrate the mean and standard deviation of one sensor; every later row is scored
as ``|x - mean| / std``; an alarm is raised where ``score >= threshold`` after the w3d4
post-processing (merge gaps of up to ``merge_gap`` rows, then drop events shorter than
``min_duration`` rows). Everything that defines that behaviour lives in ONE object, ``Detector``,
whose configuration is plain data (``to_config`` / ``from_config``).

Contract (the checks rely on it)
--------------------------------
``INPUT_COLUMNS``
    ``("run_id", "datetime", <the 8 SENSOR_COLUMNS in their canonical order>)``.

``validate_input(df) -> DataFrame``
    The inference boundary. Raises ``SchemaError`` (a ``ValueError``) when

    * columns are missing  -> the message names every missing column;
    * columns are unexpected -> the message names every unexpected column;
    * the set is right but the order is not -> the message contains the word "order";
    * there are no rows;
    * a sensor column holds a value that is not a number -> the message names the column
      (NaN / empty cells are allowed here: they are a per-run data problem, see ``score_batch``);
    * ``datetime`` does not parse -> the message names ``datetime``.

    Columns are never matched by position. Returns a copy with ``datetime`` parsed, ``run_id`` as
    ``str`` and sensors as ``float64``, rows in the input order.

``Detector``
    Fields: ``name``, ``version``, ``sensor``, ``n_burn``, ``threshold``, ``min_duration``,
    ``merge_gap`` and a free-form ``metadata`` dict. ``to_config()`` returns a JSON-serialisable dict
    and ``Detector.from_config(config)`` rebuilds an equal detector; ``from_config`` raises
    ``ValueError`` naming any missing field, and refuses a config whose ``input_columns`` differ from
    ``INPUT_COLUMNS``.

    ``calibrate(burn_in_rows) -> Calibration``: mean and POPULATION standard deviation (ddof=0) of
    ``sensor`` over exactly the rows given; a standard deviation of 0 becomes 1.0. This is the same
    arithmetic as the evaluated path (``flowguard.baselines.SingleSensorZScorer``).

    ``score_rows(rows, calibration) -> ndarray``: ``|x - mean| / std``, one value per row.

    ``score_batch(df) -> (frame, errors)``: ``df`` passes ``validate_input`` first. For every run
    (rows ordered by ``datetime``, ties kept in input order):

    * the first ``n_burn`` rows calibrate the run and are reported with ``status="burn_in"``,
      ``score`` NaN, ``alarm`` 0;
    * every later row has ``status="scored"``, the score from that calibration ONLY, and ``alarm`` 1
      exactly on the rows inside ``extract_events(score >= threshold, min_duration, merge_gap)``
      computed over the run's scored rows;
    * a run with ``n_burn`` rows or fewer, or with a missing value in ``sensor``, is not scored: all
      its rows get ``status="error"``, ``score`` NaN, ``alarm`` 0, and ``errors[run_id]`` says why.
      Other runs are unaffected.

    ``frame`` has the columns ``OUTPUT_COLUMNS`` and one row per input row, in the input order.
    ``threshold``, ``n_burn`` and the post-processing come from the configuration and are NEVER
    re-derived from the batch being scored.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS
from flowguard.evaluation import extract_events

INPUT_COLUMNS: tuple[str, ...] = ("run_id", "datetime", *SENSOR_COLUMNS)
OUTPUT_COLUMNS: tuple[str, ...] = (
    "run_id", "datetime", "score", "alarm", "status", "model_name", "model_version", "threshold",
)
REQUIRED_CONFIG = ("name", "version", "sensor", "n_burn", "threshold", "min_duration", "merge_gap")


class SchemaError(ValueError):
    """The input does not match the serving contract. Nothing was scored."""


def validate_input(df: pd.DataFrame) -> pd.DataFrame:
    columns = [str(c) for c in df.columns]
    expected = list(INPUT_COLUMNS)
    missing = [c for c in expected if c not in columns]
    unexpected = [c for c in columns if c not in expected]
    problems = []
    if missing:
        problems.append(f"missing columns: {missing}")
    if unexpected:
        problems.append(f"unexpected columns: {unexpected}")
    if problems:
        raise SchemaError("; ".join(problems) + f". Expected exactly {expected}")
    if columns != expected:
        raise SchemaError(f"columns are in the wrong order: got {columns}, expected {expected}")
    if len(df) == 0:
        raise SchemaError("the input has no rows")
    out = df.copy()
    out["run_id"] = out["run_id"].astype(str)
    for column in SENSOR_COLUMNS:
        numeric = pd.to_numeric(out[column], errors="coerce")
        bad = numeric.isna() & out[column].notna() & (out[column].astype(str).str.strip() != "")
        if bad.any():
            example = out.loc[bad, column].iloc[0]
            raise SchemaError(f"column {column!r} holds a non-numeric value, e.g. {example!r}")
        out[column] = numeric.astype("float64")
    try:
        out["datetime"] = pd.to_datetime(out["datetime"])
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"column 'datetime' does not parse: {exc}") from None
    return out


@dataclass(frozen=True)
class Calibration:
    mean: float
    std: float


@dataclass
class Detector:
    name: str
    version: str
    sensor: str = "flow_rate"
    n_burn: int = 100
    threshold: float = float("nan")
    min_duration: int = 1
    merge_gap: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sensor not in SENSOR_COLUMNS:
            raise ValueError(f"unknown sensor {self.sensor!r}")
        if int(self.n_burn) < 2:
            raise ValueError("n_burn must be at least 2")
        if int(self.min_duration) < 1 or int(self.merge_gap) < 0:
            raise ValueError("min_duration must be >= 1 and merge_gap >= 0")
        self.n_burn, self.min_duration, self.merge_gap = int(self.n_burn), int(self.min_duration), int(self.merge_gap)
        self.threshold = float(self.threshold)

    # ------------------------------------------------------------------ configuration as data
    def to_config(self) -> dict[str, Any]:
        return {
            "name": self.name, "version": self.version, "sensor": self.sensor, "n_burn": self.n_burn,
            "threshold": self.threshold, "min_duration": self.min_duration, "merge_gap": self.merge_gap,
            "input_columns": list(INPUT_COLUMNS), "metadata": dict(self.metadata),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Detector":
        missing = [k for k in REQUIRED_CONFIG if k not in config]
        if missing:
            raise ValueError(f"model configuration is missing {missing}")
        columns = config.get("input_columns", list(INPUT_COLUMNS))
        if list(columns) != list(INPUT_COLUMNS):
            raise ValueError(f"model was built for input columns {list(columns)}, this code serves {list(INPUT_COLUMNS)}")
        return cls(**{k: config[k] for k in REQUIRED_CONFIG}, metadata=dict(config.get("metadata", {})))

    # ------------------------------------------------------------------ the scoring path
    def calibrate(self, burn_in_rows: pd.DataFrame) -> Calibration:
        x = burn_in_rows[self.sensor].to_numpy(dtype=float)
        std = float(x.std())                      # population std, as in the evaluated path
        return Calibration(mean=float(x.mean()), std=std if std > 0 else 1.0)

    def score_rows(self, rows: pd.DataFrame, calibration: Calibration) -> np.ndarray:
        x = rows[self.sensor].to_numpy(dtype=float)
        return np.abs((x - calibration.mean) / calibration.std)

    def alarm_mask(self, scores: np.ndarray) -> np.ndarray:
        mask = np.zeros(len(scores), dtype=np.int64)
        for start, end in extract_events(scores >= self.threshold, self.min_duration, self.merge_gap):
            mask[start:end] = 1
        return mask

    def score_batch(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
        data = validate_input(df).reset_index(drop=True)
        n = len(data)
        score = np.full(n, np.nan)
        alarm = np.zeros(n, dtype=np.int64)
        status = np.full(n, "scored", dtype=object)
        errors: dict[str, str] = {}
        for run_id, run in data.groupby("run_id", sort=False):
            run = run.sort_values("datetime", kind="stable")
            idx = run.index.to_numpy()
            if len(run) <= self.n_burn:
                errors[run_id] = f"{len(run)} rows; at least {self.n_burn + 1} are needed (burn-in {self.n_burn})"
            elif run[self.sensor].isna().any():
                errors[run_id] = f"missing values in {self.sensor!r}"
            if run_id in errors:
                status[idx] = "error"
                continue
            calibration = self.calibrate(run)
            rest = run.iloc[self.n_burn:]
            s = self.score_rows(rest, calibration)
            status[idx[: self.n_burn]] = "burn_in"
            score[rest.index.to_numpy()] = s
            alarm[rest.index.to_numpy()] = self.alarm_mask(s)
        frame = pd.DataFrame({
            "run_id": data["run_id"], "datetime": data["datetime"], "score": score, "alarm": alarm,
            "status": status, "model_name": self.name, "model_version": self.version,
            "threshold": self.threshold,
        })
        return frame[list(OUTPUT_COLUMNS)], errors


def serving_frame(tidy: pd.DataFrame) -> pd.DataFrame:
    """The serving input for experiments of the tidy table: what a plant would send (no labels)."""
    out = tidy[["experiment_id", "datetime", *SENSOR_COLUMNS]].rename(columns={"experiment_id": "run_id"})
    return out.reset_index(drop=True)
