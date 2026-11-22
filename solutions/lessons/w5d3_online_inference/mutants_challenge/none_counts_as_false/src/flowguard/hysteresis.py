"""Alarm hysteresis for a stream of threshold exceedances. REFERENCE SOLUTION (w5d3 challenge)."""
from __future__ import annotations

import math

import numpy as np


class AlarmHysteresis:
    def __init__(self, k_raise: int, m_clear: int):
        for name, value in (("k_raise", k_raise), ("m_clear", m_clear)):
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
                raise ValueError(f"{name} must be an integer >= 1, got {value!r}")
        self.k_raise, self.m_clear = int(k_raise), int(m_clear)
        self._alarm, self._run_hi, self._run_lo = False, 0, 0

    @property
    def alarm(self) -> bool:
        return self._alarm

    def update(self, exceeds: bool | None) -> bool:
        if exceeds:
            self._run_hi, self._run_lo = self._run_hi + 1, 0
            if not self._alarm and self._run_hi >= self.k_raise:
                self._alarm = True
        else:
            self._run_hi, self._run_lo = 0, self._run_lo + 1
            if self._alarm and self._run_lo >= self.m_clear:
                self._alarm = False
        return self._alarm

    def snapshot(self) -> dict:
        return {"k_raise": self.k_raise, "m_clear": self.m_clear, "alarm": self._alarm,
                "run_hi": self._run_hi, "run_lo": self._run_lo}

    @classmethod
    def restore(cls, snapshot: dict) -> "AlarmHysteresis":
        h = cls(snapshot["k_raise"], snapshot["m_clear"])
        h._alarm, h._run_hi, h._run_lo = bool(snapshot["alarm"]), int(snapshot["run_hi"]), int(snapshot["run_lo"])
        return h


def _as_optional_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and math.isnan(value):
        return None
    return bool(value)


def hysteresis_batch(exceeds, k_raise: int, m_clear: int) -> np.ndarray:
    h = AlarmHysteresis(k_raise, m_clear)          # one code path: batch IS the streaming rule
    return np.array([h.update(_as_optional_bool(v)) for v in exceeds], dtype=bool)
