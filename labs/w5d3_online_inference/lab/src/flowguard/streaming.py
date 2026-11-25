"""Stateful, one-sample-at-a-time scoring with parity to ``Detector.score_batch``.

YOU IMPLEMENT THIS MODULE (lesson w5d3). This docstring is the contract; the checks test it.

Parity (the core guarantee)
---------------------------
Feeding a run's rows, in order, one at a time to ``StreamScorer.update`` must give the same scores as
``detector.score_batch(run)``: ``None`` exactly where batch gives NaN (the first ``n_burn`` samples),
and otherwise equal within ``rtol=1e-9, atol=1e-9``. Calibration uses the population SD (``ddof=0``)
of the first ``n_burn`` accepted values, and ``sigma = 1`` if that SD is 0, exactly like batch.

State must be O(1) in the stream length: running accumulators (Welford: count, mean, M2), the frozen
``mu``/``sigma``, the last timestamp/value/result. Never a list of past values.

``ScoreResult`` (frozen dataclass)
    machine_id: str | None, timestamp: pd.Timestamp, score: float | None,
    status: "warming_up" | "ok", exceeds: bool | None (score >= detector.threshold; None if no score),
    n_seen: int (accepted samples so far, this one included), after_gap: bool = False,
    duplicate: bool = False

``StreamScorer(detector, machine_id=None, max_gap_s=5.0, gap_policy="flag")``
    ``update(row) -> ScoreResult``. ``row`` is a mapping with ``"datetime"`` (anything ``pd.Timestamp``
    accepts) and ``detector.sensor``; other keys are ignored. Rules, in this order:

    1. Missing timestamp or sensor value, or a value that is not a finite number:
       raise ``InvalidSampleError``.
    2. Timestamp earlier than the last accepted one: raise ``OutOfOrderError``.
    3. Timestamp equal to the last accepted one: if the value is also equal, return the last
       result again with ``duplicate=True`` (idempotent: the state does not change); otherwise raise
       ``ConflictingDuplicateError``.
    4. More than ``max_gap_s`` seconds after the last accepted sample: ``after_gap=True``. With
       ``gap_policy="flag"`` scoring continues unchanged. With ``gap_policy="reset"`` calibration
       restarts: this sample is the first of a new burn-in.
    5. Otherwise accept the sample: warm-up (``score=None``, ``status="warming_up"``) until
       ``n_burn`` values have been accumulated, then ``|x - mu| / sigma`` with ``status="ok"``.

    Every rejection (rules 1-3) leaves the state exactly as it was.
    ``ValueError`` for an unknown ``gap_policy`` or a non-positive ``max_gap_s``.

    ``snapshot() -> dict``: everything needed to continue, JSON-serialisable (``json.dumps`` works).
    ``StreamScorer.restore(detector, snapshot) -> StreamScorer``: a scorer whose future results are
    identical to those of the scorer that was snapshotted. ``ValueError`` if the snapshot was taken
    with a different ``detector.version``.

Exceptions: ``StreamError(ValueError)`` with subclasses ``InvalidSampleError``, ``OutOfOrderError``,
``ConflictingDuplicateError``; ``UnknownMachineError(KeyError)``.

``StreamRegistry(detector, **scorer_kwargs)``: one ``StreamScorer`` per machine id.
    ``register(machine_id) -> bool`` (True if new; registering again keeps the state and returns False),
    ``get(machine_id) -> StreamScorer``, ``update(machine_id, row) -> ScoreResult``,
    ``remove(machine_id)``, ``machines() -> list[str]`` (sorted). An unregistered id raises
    ``UnknownMachineError`` in ``get``/``update``/``remove``. ``snapshot() -> dict`` and
    ``StreamRegistry.restore(detector, snapshot, **scorer_kwargs)`` as for one scorer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from flowguard.inference import Detector


class StreamError(ValueError):
    """A sample was rejected; the scorer's state is unchanged."""


class InvalidSampleError(StreamError):
    pass


class OutOfOrderError(StreamError):
    pass


class ConflictingDuplicateError(StreamError):
    pass


class UnknownMachineError(KeyError):
    pass


@dataclass(frozen=True)
class ScoreResult:
    machine_id: str | None
    timestamp: pd.Timestamp
    score: float | None
    status: str
    exceeds: bool | None
    n_seen: int
    after_gap: bool = False
    duplicate: bool = False


class StreamScorer:
    def __init__(self, detector: Detector, machine_id: str | None = None, max_gap_s: float = 5.0,
                 gap_policy: str = "flag"):
        raise NotImplementedError("TODO (task 1): store the configuration and initialise O(1) state")

    def update(self, row: Mapping) -> ScoreResult:
        raise NotImplementedError("TODO (tasks 2-4)")

    def snapshot(self) -> dict:
        raise NotImplementedError("TODO (task 5)")

    @classmethod
    def restore(cls, detector: Detector, snapshot: dict) -> "StreamScorer":
        raise NotImplementedError("TODO (task 5)")


class StreamRegistry:
    def __init__(self, detector: Detector, **scorer_kwargs):
        raise NotImplementedError("TODO (task 6)")
