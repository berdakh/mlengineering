"""Stateful, one-sample-at-a-time scoring with parity to ``Detector.score_batch``.

REFERENCE SOLUTION for lesson w5d3. The contract is the module docstring of the lab starter.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Mapping

import pandas as pd

from flowguard.inference import Detector

SNAPSHOT_FORMAT = 1
GAP_POLICIES = ("flag", "reset")


class StreamError(ValueError):
    """A sample was rejected; the scorer's state is unchanged."""


class InvalidSampleError(StreamError):
    """Missing timestamp or sensor value, or a value that is not a finite number."""


class OutOfOrderError(StreamError):
    """The sample's timestamp is earlier than the last accepted timestamp."""


class ConflictingDuplicateError(StreamError):
    """Same timestamp as the last accepted sample, but a different value."""


class UnknownMachineError(KeyError):
    """The registry has no stream with this id."""


@dataclass(frozen=True)
class ScoreResult:
    machine_id: str | None
    timestamp: pd.Timestamp
    score: float | None
    status: str                 # "warming_up" or "ok"
    exceeds: bool | None        # score >= detector.threshold; None when there is no score
    n_seen: int                 # samples accepted so far, this one included
    after_gap: bool = False
    duplicate: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ScoreResult":
        return cls(**{**d, "timestamp": pd.Timestamp(d["timestamp"])})


class StreamScorer:
    def __init__(self, detector: Detector, machine_id: str | None = None, max_gap_s: float = 5.0,
                 gap_policy: str = "flag"):
        if gap_policy not in GAP_POLICIES:
            raise ValueError(f"gap_policy must be one of {GAP_POLICIES}")
        if not max_gap_s > 0:
            raise ValueError("max_gap_s must be positive")
        self.detector, self.machine_id = detector, machine_id
        self.max_gap_s, self.gap_policy = float(max_gap_s), gap_policy
        self._reset_calibration()
        self.n_seen = 0
        self.last_ts: pd.Timestamp | None = None
        self.last_value: float | None = None
        self.last_result: ScoreResult | None = None

    # -- state ---------------------------------------------------------------------------------
    def _reset_calibration(self) -> None:
        self.count, self.mean, self.m2 = 0, 0.0, 0.0      # Welford accumulators over the burn-in
        self.mu: float | None = None                      # frozen once count == n_burn
        self.sigma: float | None = None

    def _parse(self, row: Mapping) -> tuple[pd.Timestamp, float]:
        try:
            ts = pd.Timestamp(row["datetime"])
            value = float(row[self.detector.sensor])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidSampleError(f"sample needs 'datetime' and a numeric {self.detector.sensor!r}: {exc}") from exc
        if pd.isna(ts):
            raise InvalidSampleError("timestamp is missing")
        if not math.isfinite(value):
            raise InvalidSampleError(f"{self.detector.sensor} is not a finite number: {value!r}")
        return ts, value

    # -- the one public operation ----------------------------------------------------------------
    def update(self, row: Mapping) -> ScoreResult:
        ts, value = self._parse(row)
        after_gap = False
        if self.last_ts is not None:
            if ts < self.last_ts:
                raise OutOfOrderError(f"timestamp {ts} is earlier than the last accepted {self.last_ts}")
            if ts == self.last_ts and value != self.last_value:
                raise ConflictingDuplicateError(f"timestamp {ts} already accepted with a different value")
            if (ts - self.last_ts).total_seconds() > self.max_gap_s:
                after_gap = True
                if self.gap_policy == "reset":
                    self._reset_calibration()

        if self.mu is None:                                # still calibrating: Welford update
            self.count += 1
            delta = value - self.mean
            self.mean += delta / self.count
            self.m2 += delta * (value - self.mean)
            if self.count == self.detector.n_burn:
                self.mu = self.mean
                sigma = math.sqrt(self.m2 / self.count)
                self.sigma = sigma if sigma > 0 else 1.0
            score, status, exceeds = None, "warming_up", None
        else:
            score = abs(value - self.mu) / self.sigma
            status, exceeds = "ok", score >= self.detector.threshold

        self.n_seen += 1
        self.last_ts, self.last_value = ts, value
        self.last_result = ScoreResult(self.machine_id, ts, score, status, exceeds, self.n_seen, after_gap)
        return self.last_result

    # -- persistence -------------------------------------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "format": SNAPSHOT_FORMAT, "detector_version": self.detector.version,
            "machine_id": self.machine_id, "max_gap_s": self.max_gap_s, "gap_policy": self.gap_policy,
            "count": self.count, "mean": self.mean, "m2": self.m2, "mu": self.mu, "sigma": self.sigma,
            "n_seen": self.n_seen,
            "last_ts": None if self.last_ts is None else self.last_ts.isoformat(),
            "last_value": self.last_value,
            "last_result": None if self.last_result is None else self.last_result.to_dict(),
        }

    @classmethod
    def restore(cls, detector: Detector, snapshot: dict) -> "StreamScorer":
        if snapshot.get("format") != SNAPSHOT_FORMAT:
            raise ValueError(f"unsupported snapshot format {snapshot.get('format')!r}")
        if snapshot.get("detector_version") != detector.version:
            raise ValueError(f"snapshot was taken with detector {snapshot.get('detector_version')!r}, "
                             f"not {detector.version!r}")
        s = cls(detector, snapshot["machine_id"], snapshot["max_gap_s"], snapshot["gap_policy"])
        s.count, s.mean, s.m2 = snapshot["count"], snapshot["mean"], snapshot["m2"]
        s.mu, s.sigma, s.n_seen = snapshot["mu"], snapshot["sigma"], snapshot["n_seen"]
        s.last_ts = None if snapshot["last_ts"] is None else pd.Timestamp(snapshot["last_ts"])
        s.last_value = snapshot["last_value"]
        s.last_result = None if snapshot["last_result"] is None else ScoreResult.from_dict(snapshot["last_result"])
        return s


class StreamRegistry:
    """One ``StreamScorer`` per machine id. Machines must be registered before they send samples."""

    def __init__(self, detector: Detector, **scorer_kwargs):
        self.detector, self.scorer_kwargs = detector, scorer_kwargs
        self._streams: dict[str, StreamScorer] = {}

    def register(self, machine_id: str) -> bool:
        """Create a stream; ``True`` if it is new, ``False`` if it already existed (state kept)."""
        if machine_id in self._streams:
            return False
        self._streams[machine_id] = StreamScorer(self.detector, machine_id, **self.scorer_kwargs)
        return True

    def get(self, machine_id: str) -> StreamScorer:
        try:
            return self._streams[machine_id]
        except KeyError:
            raise UnknownMachineError(machine_id) from None

    def update(self, machine_id: str, row: Mapping) -> ScoreResult:
        return self.get(machine_id).update(row)

    def remove(self, machine_id: str) -> None:
        self.get(machine_id)
        del self._streams[machine_id]

    def machines(self) -> list[str]:
        return sorted(self._streams)

    def snapshot(self) -> dict:
        return {"format": SNAPSHOT_FORMAT, "streams": {m: s.snapshot() for m, s in self._streams.items()}}

    @classmethod
    def restore(cls, detector: Detector, snapshot: dict, **scorer_kwargs) -> "StreamRegistry":
        reg = cls(detector, **scorer_kwargs)
        for machine_id, snap in snapshot["streams"].items():
            reg._streams[machine_id] = StreamScorer.restore(detector, snap)
        return reg
