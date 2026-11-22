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
    """Task 1. See the module docstring. Never match columns by position."""
    raise NotImplementedError("Task 1: validate_input")


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

    # ------------------------------------------------------------------ configuration as data (given)
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

    # ------------------------------------------------------------------ the scoring path (Task 2)
    def calibrate(self, burn_in_rows: pd.DataFrame) -> Calibration:
        """Mean and POPULATION std (ddof=0) of ``self.sensor`` over exactly these rows; std 0 -> 1.0."""
        raise NotImplementedError("Task 2: calibrate")

    def score_rows(self, rows: pd.DataFrame, calibration: Calibration) -> np.ndarray:
        """|x - mean| / std of ``self.sensor``, one value per row."""
        raise NotImplementedError("Task 2: score_rows")

    def alarm_mask(self, scores: np.ndarray) -> np.ndarray:
        """0/1 per score: 1 inside extract_events(scores >= threshold, min_duration, merge_gap)."""
        raise NotImplementedError("Task 2: alarm_mask")

    def score_batch(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
        """Task 3. See the module docstring: per-run calibration, per-run failure, input order kept."""
        raise NotImplementedError("Task 3: score_batch")


def serving_frame(tidy: pd.DataFrame) -> pd.DataFrame:
    """The serving input for experiments of the tidy table: what a plant would send (no labels). Given."""
    out = tidy[["experiment_id", "datetime", *SENSOR_COLUMNS]].rename(columns={"experiment_id": "run_id"})
    return out.reset_index(drop=True)
