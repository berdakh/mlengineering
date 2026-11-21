"""w2d3 independent challenge: data-quality checks for an orders export.  <-- YOU WRITE THIS

See README.md in this directory for the data contract and the acceptance criteria.
"""
from __future__ import annotations

import pandas as pd


def run_checks(orders: pd.DataFrame) -> list:
    """Return one result object per contract rule.

    ``orders`` is the export read as text: pd.read_csv(path, dtype=str, keep_default_na=False).
    Each result has the attributes ``name``, ``passed``, ``severity`` ("error" | "warning"), ``detail``.
    """
    raise NotImplementedError


if __name__ == "__main__":
    import sys
    table = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False)
    for r in run_checks(table):
        print(f"{'ok  ' if r.passed else 'FAIL'} [{r.severity:7}] {r.name}: {r.detail}")
