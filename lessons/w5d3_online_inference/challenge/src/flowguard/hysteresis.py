"""Alarm hysteresis for a stream of threshold exceedances. YOU IMPLEMENT THIS (w5d3 challenge).

Contract (the checks test it)
-----------------------------
``AlarmHysteresis(k_raise, m_clear)``; both must be integers >= 1, else ``ValueError``.
The alarm starts OFF. ``update(exceeds) -> bool`` takes one sample's ``exceeds`` (``True``, ``False``
or ``None`` for "no score", e.g. warm-up) and returns the alarm state AFTER this sample:

* ``True``: the run of consecutive ``True`` grows by one and the run of consecutive ``False`` is
  reset to 0. If the alarm is OFF and the ``True`` run has reached ``k_raise``, the alarm turns ON.
* ``False``: symmetric. If the alarm is ON and the ``False`` run has reached ``m_clear``, it turns OFF.
* ``None``: both runs reset to 0 and the alarm state is unchanged (no evidence either way).

``alarm`` (property): the current state.
``snapshot() -> dict`` / ``AlarmHysteresis.restore(snapshot)``: JSON-serialisable state; a restored
object continues identically.

``hysteresis_batch(exceeds, k_raise, m_clear) -> np.ndarray`` (dtype bool): the alarm state after each
element of a whole sequence. It MUST equal feeding the sequence to ``AlarmHysteresis.update`` one
element at a time. ``exceeds`` may be a list containing None, or a float array where NaN means None.
"""
from __future__ import annotations

import numpy as np


class AlarmHysteresis:
    def __init__(self, k_raise: int, m_clear: int):
        raise NotImplementedError("TODO")

    def update(self, exceeds: bool | None) -> bool:
        raise NotImplementedError("TODO")


def hysteresis_batch(exceeds, k_raise: int, m_clear: int) -> np.ndarray:
    raise NotImplementedError("TODO")
