"""ingest: validates before writing, fails loudly, records provenance, and is idempotent."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

import synth

TIDY_COLUMNS = ["experiment_id", "family", "t", "datetime", "accelerometer1_rms", "accelerometer2_rms",
                "current", "pressure", "temperature", "thermocouple", "voltage", "flow_rate", "anomaly", "changepoint"]
OUTPUTS = ("skab.csv", "quality_report.json", "provenance.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root: Path) -> dict:
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def test_clean_ingest_writes_the_three_outputs(raw_dir, ingest_cli, tmp_path):
    raw, out = raw_dir(), tmp_path / "interim"
    proc = ingest_cli(raw, out)
    assert proc.returncode == 0, proc.stderr[-1500:]
    for name in OUTPUTS:
        assert (out / name).is_file(), f"{name} was not written"
    tidy = pd.read_csv(out / "skab.csv")
    assert list(tidy.columns) == TIDY_COLUMNS
    assert len(tidy) == 4 * synth.N_ROWS
    assert set(tidy["family"]) == {"anomaly-free", "other", "valve1"}
    assert set(tidy["anomaly"].unique()) <= {0, 1} and set(tidy["changepoint"].unique()) <= {0, 1}
    assert str(tidy["anomaly"].dtype).startswith("int"), "labels must be stored as integers"
    assert (tidy.loc[tidy["family"] == "anomaly-free", "anomaly"] == 0).all()
    stamps = pd.to_datetime(tidy["datetime"], format="%Y-%m-%d %H:%M:%S")
    assert tidy["experiment_id"].is_monotonic_increasing
    assert stamps.groupby(tidy["experiment_id"]).apply(lambda s: s.is_monotonic_increasing).all()
    assert (tidy.groupby("experiment_id")["t"].apply(list).map(lambda t: t == list(range(len(t))))).all()


def test_quality_report_is_machine_readable(raw_dir, ingest_cli, tmp_path):
    out = tmp_path / "interim"
    assert ingest_cli(raw_dir("gap_300s"), out).returncode == 0, "a warning must not stop ingestion"
    report = json.loads((out / "quality_report.json").read_text())
    results = report["results"]
    assert isinstance(results, list) and len(results) >= 6
    for r in results:
        assert {"name", "passed", "severity", "detail"} <= set(r)
    failing = [r for r in results if not r["passed"]]
    assert failing and all(r["severity"] == "warning" for r in failing)
    assert any(synth.BAD in r["detail"] for r in failing)
    assert (out / "skab.csv").is_file(), "warnings are recorded, and the table is still written"


def test_provenance_ties_output_to_inputs(raw_dir, ingest_cli, tmp_path):
    raw, out = raw_dir(), tmp_path / "interim"
    assert ingest_cli(raw, out).returncode == 0
    text = (out / "provenance.json").read_text()
    json.loads(text)
    for path in raw.glob("*/*.csv"):
        assert sha(path) in text, f"provenance does not contain the sha256 of input {path.parent.name}/{path.name}"
    assert sha(out / "skab.csv") in text, "provenance does not contain the sha256 of the table it describes"
    for value in synth.MANIFEST.values():
        assert value in text, f"upstream record {value!r} from MANIFEST.json is not carried into provenance"


def test_ingest_is_idempotent(raw_dir, ingest_cli, tmp_path):
    raw = raw_dir("gap_300s")
    a, b = tmp_path / "a", tmp_path / "b"
    assert ingest_cli(raw, a).returncode == 0 and ingest_cli(raw, b).returncode == 0
    assert tree(a) == tree(b), "two runs on the same input must give byte-identical outputs"
    first = tree(a)
    assert ingest_cli(raw, a).returncode == 0
    assert tree(a) == first, "re-running into the same directory must not change anything"


def test_raw_is_never_modified(raw_dir, ingest_cli, tmp_path):
    raw = raw_dir("unsorted_rows")
    before = tree(raw)
    ingest_cli(raw, tmp_path / "interim")
    assert tree(raw) == before, "ingest must not write to, or repair, the raw directory"


def test_errors_stop_the_pipeline_loudly(raw_dir, ingest_cli, tmp_path):
    for defect in ("duplicate_timestamps", "unsorted_rows", "non_binary_label"):
        out = tmp_path / f"out_{defect}"
        proc = ingest_cli(raw_dir(defect), out)
        assert proc.returncode != 0, f"{defect}: ingest must exit non-zero on an error-severity failure"
        assert not (out / "skab.csv").exists(), f"{defect}: no table may be written when an error check fails"
        assert synth.BAD in proc.stderr, f"{defect}: stderr should say which experiment is broken"
        assert "Traceback" not in proc.stderr, "report the failure; do not dump a traceback on bad data"
        report = json.loads((out / "quality_report.json").read_text())
        assert any(not r["passed"] and r["severity"] == "error" for r in report["results"])


def test_no_stale_table_survives_a_failed_rerun(raw_dir, ingest_cli, tmp_path):
    out = tmp_path / "interim"
    assert ingest_cli(raw_dir(), out).returncode == 0 and (out / "skab.csv").is_file()
    assert ingest_cli(raw_dir("duplicate_timestamps"), out).returncode != 0
    assert not (out / "skab.csv").exists(), \
        "a table from an earlier good run must not sit next to a failing quality report"


def test_missing_raw_column_is_an_error_that_names_it(tmp_path, ingest_cli):
    raw = synth.write_raw(tmp_path / "raw", synth.frames_with("missing_column"))
    out = tmp_path / "interim"
    proc = ingest_cli(raw, out)
    assert proc.returncode != 0
    assert "pressure" in proc.stderr.lower(), "the message must name the missing column"
    assert "Traceback" not in proc.stderr
    assert not (out / "skab.csv").exists()


def test_missing_raw_directory_is_a_clean_error(tmp_path, ingest_cli):
    proc = ingest_cli(tmp_path / "does_not_exist", tmp_path / "interim")
    assert proc.returncode != 0 and "Traceback" not in proc.stderr and proc.stderr.strip()
