"""raw -> interim: one re-runnable step that validates before it writes.

Outputs in ``out_dir``:
    quality_report.json   always written
    skab.csv              tidy table; written only if no error-severity check failed
    provenance.json       where the bytes came from and what was produced; same condition

No wall-clock time is written to any output, so running twice on the same input
gives byte-identical files (idempotence you can test with a hash).
"""
from __future__ import annotations

import hashlib
import io
import json
import platform
from pathlib import Path

import pandas as pd

from flowguard import __version__
from flowguard.data import DATETIME_FORMAT, LABEL_COLUMNS, load_raw
from flowguard.quality import run_checks, summarise


class QualityError(RuntimeError):
    """Raised by ``ingest`` when an error-severity check fails. Carries the report."""

    def __init__(self, report: dict):
        self.report = report
        names = [r["name"] for r in report["results"] if not r["passed"] and r["severity"] == "error"]
        super().__init__(f"{len(names)} error-severity quality check(s) failed: {', '.join(names)}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _tidy_csv_bytes(tidy: pd.DataFrame) -> bytes:
    out = tidy.copy()
    for col in LABEL_COLUMNS:
        out[col] = out[col].astype("int64")
    buf = io.StringIO()
    out.to_csv(buf, index=False, lineterminator="\n", date_format=DATETIME_FORMAT)
    return buf.getvalue().encode("utf-8")


def ingest(raw_dir: str | Path, out_dir: str | Path) -> dict:
    """Validate and convert. Returns the provenance record; raises QualityError on errors."""
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    tidy = load_raw(raw_dir)                      # FileNotFoundError / ValueError propagate
    report = summarise(run_checks(tidy))
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "quality_report.json", report)
    if report["n_failed_errors"]:
        # Never leave a stale table from an earlier run next to a failing report.
        for name in ("skab.csv", "provenance.json"):
            (out_dir / name).unlink(missing_ok=True)
        raise QualityError(report)

    data = _tidy_csv_bytes(tidy)
    (out_dir / "skab.csv").write_bytes(data)

    upstream = {}
    manifest_path = raw_dir / "MANIFEST.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        upstream = {k: manifest.get(k) for k in ("source", "commit", "licence")}
    files = {}
    for path in sorted(raw_dir.glob("*/*.csv")):
        exp = f"{path.parent.name}/{path.stem}"
        files[exp] = {"sha256": _sha256_bytes(path.read_bytes()),
                      "rows": int((tidy["experiment_id"] == exp).sum())}
    provenance = {
        "source": upstream.get("source"),
        "commit": upstream.get("commit"),
        "licence": upstream.get("licence"),
        "inputs": files,
        "n_experiments": len(files),
        "n_rows": int(len(tidy)),
        "output": {"file": "skab.csv", "sha256": _sha256_bytes(data), "rows": int(len(tidy))},
        "quality": {k: report[k] for k in ("n_checks", "n_failed_errors", "n_failed_warnings")},
        "code": {"flowguard": __version__, "python": platform.python_version(), "pandas": pd.__version__},
    }
    _write_json(out_dir / "provenance.json", provenance)
    return provenance
