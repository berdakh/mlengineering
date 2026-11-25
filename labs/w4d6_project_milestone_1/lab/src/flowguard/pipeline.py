"""Milestone-1 pipeline: raw files -> tidy table -> results.json -> reports/evaluation.md.

Three steps, each a command (see cli.py) and a Makefile target:

    ingest    raw SKAB files       -> data/interim/skab.csv     (deterministic CSV)
    evaluate  tidy CSV + manifest  -> results/results.json      (ALL numbers are computed here)
    report    results.json         -> reports/evaluation.md + reports/figures/*.svg
                                      (formats numbers; computes nothing)

Contract the checks rely on (everything else is your design):
* ``results.json`` has ``provenance.splits_sha256`` (sha256 of the manifest file's bytes) and
  ``protocol.test_experiments`` (the manifest's test list), and is identical when rebuilt from the
  same inputs: no wall-clock times, no host-dependent measurements.
* every number shown in a table of ``evaluation.md`` is a value in ``results.json``, shown at the
  precision printed (so 0.8841 may appear as 0.884, never as 88.4 %).
* the report has the sections Problem, Data, Protocol, Results, Error analysis, Decision,
  Limitations, Provenance, and links at least one figure that exists.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from importlib import metadata
from pathlib import Path

import pandas as pd

from flowguard.data import load_raw

# Everything you need is already in the package (snapshots of Weeks 2-4):
#   flowguard.detectors   candidates(), score_experiments()          (w4d5)
#   flowguard.operating   choose_operating_point()                   (w3d4)
#   flowguard.evaluation  evaluate_experiments()                     (w3d4)
#   flowguard.uncertainty cluster_bootstrap(), paired_bootstrap_diff(), wilson_interval()   (w3d5)
#   flowguard.decision    decision_table(), recommend(), model_size_bytes()                 (w4d5)
#   flowguard.splits      load_splits(), validate_splits(), dev_experiments()
#   flowguard.svgplot     interval_plot()   (dependency-free, reproducible SVG)
# labs/w4d5_model_choice/lab/decision_table.py is a working script to borrow from.

MPID = 0.05
BUDGET_HOURS = 8              # at most one false alarm per this many hours of normal operation
SCHEMA = "flowguard-evaluation/1"


# --------------------------------------------------------------------------- ingest
def ingest(raw_dir: str | Path, out: str | Path) -> Path:
    """Raw SKAB files -> one tidy CSV. Same input files, same output bytes."""
    tidy = load_raw(raw_dir)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tidy.to_csv(out, index=False, lineterminator="\n", date_format="%Y-%m-%d %H:%M:%S")
    return out


def read_tidy(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["datetime"])


# --------------------------------------------------------------------------- helpers (given)
def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_results(results: dict, path: str | Path) -> Path:
    """Deterministic JSON: sorted keys, fixed indentation, no NaN/inf (store None instead)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return path


# --------------------------------------------------------------------------- yours
def provenance(splits_path: str | Path, tidy_path: str | Path) -> dict:
    """What a reader needs to rebuild the numbers: at least ``splits_sha256`` (sha256 of the manifest
    file), a hash of the tidy data, the Python and package versions, and the code version
    (``git describe --always --dirty``, or "unknown" outside a repository). No timestamps."""
    raise NotImplementedError("TODO: provenance")


def evaluate(tidy_path: str | Path, splits_path: str | Path, burn_in: int = 100, n_boot: int = 2000,
             seed: int = 0) -> dict:
    """Compute EVERY number the report will show and return them in one JSON-serialisable dict.

    Required keys: ``provenance`` (see above) and ``protocol.test_experiments`` (the manifest's test
    list, sorted). The rest is your design; the README lists what the report must contain.
    Development data chooses the operating points and the model; the test set is looked at once.
    """
    raise NotImplementedError("TODO: evaluate")


def render(results: dict, out: str | Path) -> Path:
    """Write the markdown report to ``out`` and its figures to ``out.parent / "figures"``.

    Formats numbers from ``results``; computes nothing new. Remember that a bare '|' inside a
    table cell breaks a markdown table (escape it as '\\|').
    """
    raise NotImplementedError("TODO: render")
