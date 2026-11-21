"""raw -> interim: one re-runnable step that validates before it writes.  <-- YOU IMPLEMENT THIS (task 4)

Contract (graded by `python wb.py check w2d3`):

Outputs in ``out_dir``:
    quality_report.json   always written: {"results": [{"name", "passed", "severity", "detail"}, ...], ...}
    skab.csv              the tidy table (columns ``flowguard.data.TIDY_COLUMNS``, integer labels,
                          datetime as YYYY-MM-DD HH:MM:SS); ONLY if no error-severity check failed
    provenance.json       source/commit/licence from raw_dir/MANIFEST.json when present, sha256 and
                          row count per input file, sha256 and row count of skab.csv, code versions

* A failed error check: raise ``QualityError``; no skab.csv may exist in ``out_dir`` afterwards,
  including one left by an earlier successful run.
* Idempotent: same input -> byte-identical outputs. (What must therefore NOT be in the files?)
* ``raw_dir`` is read-only.
"""
from __future__ import annotations

from pathlib import Path


class QualityError(RuntimeError):
    """Raised by ``ingest`` when an error-severity check fails. Carries the report dict."""

    def __init__(self, report: dict):
        self.report = report
        names = [r["name"] for r in report["results"] if not r["passed"] and r["severity"] == "error"]
        super().__init__(f"{len(names)} error-severity quality check(s) failed: {', '.join(names)}")


def ingest(raw_dir: str | Path, out_dir: str | Path) -> dict:
    """Validate and convert. Returns the provenance record; raises QualityError on errors."""
    raise NotImplementedError("lab task 4")
