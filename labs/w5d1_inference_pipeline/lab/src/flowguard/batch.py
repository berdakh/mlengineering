"""Batch inference: score a CSV of serving rows with a saved detector.

Contract (the checks rely on it)
--------------------------------
``predict_batch(model_dir, input_path, out_dir, *, chunk_runs=50, force=False) -> dict``

1. Load ``<model_dir>/model.json`` with ``Detector.from_config``.
2. Read the input CSV (``float_precision="round_trip"``: pandas' default parser can change the last
   digit of a float) and pass it through ``validate_input``. A ``SchemaError`` propagates and
   NOTHING is written.
3. Score the runs in chunks of ``chunk_runs`` runs (memory stays bounded by the chunk, not the
   file). The output does not depend on ``chunk_runs``.
4. Write two files into ``out_dir`` (created if needed):

   * ``predictions.csv``: ``OUTPUT_COLUMNS``, one row per input row, in the input order;
   * ``manifest.json``: at least ``format`` (``"flowguard-predictions/1"``), ``input_sha256`` (of the
     input file's bytes), ``input_rows``, ``runs``, ``runs_scored``, ``runs_failed`` (run_id -> reason),
     ``model_name``, ``model_version``, ``threshold`` and ``predictions_sha256``.

   Each file is written to a temporary name in ``out_dir`` and moved into place with ``os.replace``,
   so a reader never sees a half-written file. Nothing time-dependent goes into either file:
   running the same model on the same input twice gives byte-identical outputs.
5. If ``out_dir`` already holds a ``manifest.json`` for a DIFFERENT input or model version, raise
   ``OutputExistsError`` and change nothing, unless ``force=True``. Re-running on the same input and
   model simply rewrites identical files (the command is idempotent).

Returns the manifest dict. Runs that cannot be scored do not stop the batch; they are listed in
``runs_failed`` (the CLI exits with code 3 when that list is not empty).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path

import pandas as pd

from flowguard.inference import OUTPUT_COLUMNS, Detector, validate_input

FORMAT = "flowguard-predictions/1"


class OutputExistsError(FileExistsError):
    """``out_dir`` holds predictions for another input or model; refusing to overwrite them."""


def load_detector(model_dir: str | Path) -> Detector:
    path = Path(model_dir) / "model.json"
    if not path.is_file():
        raise FileNotFoundError(f"no model.json in {model_dir}")
    return Detector.from_config(json.loads(path.read_text()))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` to a temporary file in the same directory, then os.replace it onto ``path``."""
    raise NotImplementedError("Task 4: _atomic_write")


def predict_batch(model_dir, input_path, out_dir, *, chunk_runs: int = 50, force: bool = False) -> dict:
    """Task 4. See the module docstring."""
    raise NotImplementedError("Task 4: predict_batch")
