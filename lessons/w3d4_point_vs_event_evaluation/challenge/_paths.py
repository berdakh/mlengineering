"""Make ``flowguard`` importable for the challenge scripts.

Uses ``challenge/src`` if you copied your package there, otherwise your lab package in ``../lab/src``.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for candidate in (HERE / "src", HERE.parent / "lab" / "src"):
    if (candidate / "flowguard").is_dir():
        sys.path.insert(0, str(candidate))
        break
else:  # pragma: no cover
    raise ImportError("flowguard not found in challenge/src or ../lab/src")
