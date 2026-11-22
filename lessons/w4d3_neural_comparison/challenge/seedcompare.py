"""Seed-variance reporting and a conservative verdict for comparing two detectors. CHALLENGE STARTER.

Read challenge/README.md for the contract and acceptance criteria. Keep the function names and
signatures: the checks import them.
"""
from __future__ import annotations

from typing import Mapping


def seed_summary(values: Mapping[int, float]) -> dict:
    raise NotImplementedError


def compare(a: Mapping[int, float], b: Mapping[int, float], test_halfwidth: float) -> dict:
    raise NotImplementedError


def format_table(rows: Mapping[str, Mapping[int, float]]) -> str:
    raise NotImplementedError
