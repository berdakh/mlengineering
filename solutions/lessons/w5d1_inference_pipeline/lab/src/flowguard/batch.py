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
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def predict_batch(model_dir, input_path, out_dir, *, chunk_runs: int = 50, force: bool = False) -> dict:
    if chunk_runs < 1:
        raise ValueError("chunk_runs must be >= 1")
    detector = load_detector(model_dir)
    raw = Path(input_path).read_bytes()
    data = validate_input(pd.read_csv(io.BytesIO(raw), float_precision="round_trip"))  # SchemaError: nothing written
    input_sha = _sha256(raw)

    out = Path(out_dir)
    existing = out / "manifest.json"
    if existing.is_file() and not force:
        old = json.loads(existing.read_text())
        if old.get("input_sha256") != input_sha or old.get("model_version") != detector.version:
            raise OutputExistsError(
                f"{out} already holds predictions for input {old.get('input_sha256', '?')[:12]} with model "
                f"{old.get('model_version')}; use another --out or --force")

    runs = list(dict.fromkeys(data["run_id"]))                   # first-appearance order
    frames, errors = [], {}
    for i in range(0, len(runs), chunk_runs):
        chunk = data[data["run_id"].isin(runs[i:i + chunk_runs])]
        frame, chunk_errors = detector.score_batch(chunk)
        frames.append(frame.set_axis(chunk.index))
        errors.update(chunk_errors)
    predictions = pd.concat(frames).sort_index()[list(OUTPUT_COLUMNS)]

    csv_bytes = predictions.to_csv(index=False, lineterminator="\n").encode()
    manifest = {
        "format": FORMAT, "input_sha256": input_sha, "input_rows": int(len(data)), "runs": len(runs),
        "runs_scored": len(runs) - len(errors), "runs_failed": dict(sorted(errors.items())),
        "model_name": detector.name, "model_version": detector.version, "threshold": detector.threshold,
        "predictions_sha256": _sha256(csv_bytes),
    }
    out.mkdir(parents=True, exist_ok=True)
    _atomic_write(out / "predictions.csv", csv_bytes)
    _atomic_write(existing, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    return manifest
