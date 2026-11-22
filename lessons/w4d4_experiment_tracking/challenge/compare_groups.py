"""Paired comparison of two groups of runs from the registry index. CHALLENGE STARTER.

Read challenge/README.md for the contract and acceptance criteria. Keep the names and signatures.
"""
from __future__ import annotations

from typing import Any, Mapping

import pandas as pd


def compare_groups(index: pd.DataFrame, a: Mapping[str, Any], b: Mapping[str, Any], metric: str,
                   pair_on: str = "seed") -> dict:
    raise NotImplementedError


def format_report(result: dict, a: Mapping[str, Any], b: Mapping[str, Any]) -> str:
    raise NotImplementedError
