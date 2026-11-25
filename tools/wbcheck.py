"""Shared helper for check suites: decide which directory the checks should grade.

By default checks grade the learner's working directory (``<unit>/lab`` or
``<unit>/challenge``). Set ``WB_TARGET_DIR`` to grade another directory, which is
how ``tools/verify_checks.py`` grades the reference solution and the mutants.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_target(unit: str, part: str = "lab") -> Path:
    """``unit`` is a repo-relative path such as ``labs/w1d3_package_structure``."""
    override = os.environ.get("WB_TARGET_DIR")
    return Path(override).resolve() if override else ROOT / unit / part
