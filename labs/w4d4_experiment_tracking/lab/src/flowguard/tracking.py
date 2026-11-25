"""Sweeps, run directories and a registry rebuilt from them. LAB STARTER: complete the TODOs.

Layout of one run (the run directory is the single source of truth; the index is derived):

    <runs_dir>/<run_id>/
        config.json        the resolved configuration, including "seed", "task" and "sweep"
        environment.json   code version, interpreter, libraries, data fingerprints
        metrics.json       what the task returned (absent if the task failed)
        status.json        written LAST: {"status": "complete" | "failed", ...}

``run_id`` is the content hash of ``config.json``: the same configuration always maps to the same
directory, so a completed run is never repeated or overwritten. A directory without
``status.json`` is a run that died part-way ("partial"); it carries no evidence.

    <runs_dir>/index.csv   one row per run directory, rebuilt by ``write_index``; never read back
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import platform
import subprocess
import time
import tomllib
import traceback
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from flowguard.tasks import get_task

RESERVED = ("seed", "task", "sweep")


# ----------------------------------------------------------------------------- dotted keys (given)
def flatten(d: dict, prefix: str = "") -> dict[str, Any]:
    """{"a": {"b": 1}} -> {"a.b": 1}."""
    out: dict[str, Any] = {}
    for key, value in d.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, name + "."))
        else:
            out[name] = value
    return out


def set_dotted(d: dict, dotted: str, value: Any) -> None:
    """set_dotted(cfg, "detector.shrinkage", 0.1) creates intermediate tables as needed."""
    *parents, leaf = dotted.split(".")
    for part in parents:
        d = d.setdefault(part, {})
    d[leaf] = value


def load_spec(path: str | Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _write_json(path: Path, payload: dict) -> None:
    """Write via a temporary file and an atomic rename: readers never see half a file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ----------------------------------------------------------------------------- Task 1: identity
def config_hash(config: dict) -> str:
    """12 hex characters identifying a resolved config. Independent of key order; changes when any
    value (including the seed) changes."""
    # TODO Task 1: a canonical JSON serialisation, then sha256; keep 12 hex characters.
    raise NotImplementedError("config_hash")


def run_id(config: dict) -> str:
    return config_hash(config)


# ----------------------------------------------------------------------------- Task 2: sweep expansion
def _sample(rng: np.random.Generator, dist: dict) -> Any:
    kind = dist["dist"]
    if kind == "uniform":
        return float(rng.uniform(dist["low"], dist["high"]))
    if kind == "loguniform":
        return float(math.exp(rng.uniform(math.log(dist["low"]), math.log(dist["high"]))))
    if kind == "int":
        return int(rng.integers(dist["low"], dist["high"] + 1))
    if kind == "choice":
        return dist["values"][int(rng.integers(len(dist["values"])))]
    raise ValueError(f"unknown distribution {kind!r}")


def _flatten_space(d: dict, prefix: str = "") -> dict[str, dict]:
    """Like ``flatten``, but a table with a "dist" key is a leaf (a distribution)."""
    out: dict[str, dict] = {}
    for key, value in d.items():
        if isinstance(value, dict) and "dist" not in value:
            out.update(_flatten_space(value, f"{prefix}{key}."))
        else:
            out[f"{prefix}{key}"] = value
    return out


def expand_sweep(spec: dict) -> list[dict]:
    """Resolved per-run configs: base + one point of the grid (or one random sample) + one seed.

    Order is deterministic: grid keys sorted, values in listed order, seeds innermost.
    Every config carries "seed", "task" and "sweep".
    """
    # TODO Task 2: grid mode (itertools.product over sorted flattened grid keys) and random mode
    # (_flatten_space + _sample with np.random.default_rng(sweep["sample_seed"])); seeds innermost;
    # deep-copy the base for every run; add "seed", "task" and "sweep".
    raise NotImplementedError("expand_sweep")


# ----------------------------------------------------------------------------- provenance (given)
def _git_commit() -> str | None:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                timeout=5, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                               timeout=5, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"{commit}-dirty" if dirty else commit


def _fingerprint(path: Path) -> dict:
    if path.is_file():
        return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    manifest = path / "MANIFEST.json"
    if manifest.is_file():
        return {"manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}
    files = sorted(p for p in path.rglob("*") if p.is_file())
    listing = "\n".join(f"{p.relative_to(path)}:{p.stat().st_size}" for p in files)
    return {"listing_sha256": hashlib.sha256(listing.encode()).hexdigest(), "files": len(files)}


def collect_environment(config: dict) -> dict:
    """Everything that shaped the result but is not in the config."""
    packages = {}
    for name in ("flowguard", "numpy", "pandas", "scikit-learn"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    if packages["flowguard"] is None:
        from flowguard import __version__
        packages["flowguard"] = f"{__version__} (source tree)"
    data = {}
    for key, value in flatten(config.get("data", {})).items():
        if isinstance(value, str) and Path(value).exists():
            data[key] = {"path": value, **_fingerprint(Path(value))}
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": packages,
            "git_commit": _git_commit(), "data": data}


# ----------------------------------------------------------------------------- Task 3: execute one run
def _status(run_dir: Path) -> str:
    """"complete" | "failed" | "partial" for one run directory (used by execute, build_index, reproduce)."""
    # TODO Task 3: "complete" only if status.json says complete AND metrics.json is readable;
    # "failed" if status.json says failed; anything else (no status.json, unreadable) is "partial".
    raise NotImplementedError("_status")


def execute(config: dict, runs_dir: str | Path) -> dict:
    """Run one config into ``runs_dir/<run_id>``; return ``{"run_id", "status", "path"}``.

    * complete already -> nothing is run or written, status "skipped";
    * a partial or failed directory from an earlier attempt is cleared and the run is retried;
    * an exception in the task is recorded in status.json (status "failed"); it is not raised.
    """
    # TODO Task 3: skip complete runs; clear stale metrics/status of an earlier attempt; write
    # config.json and environment.json; run get_task(config["task"])(config) inside try/except;
    # write metrics.json, and status.json LAST. Use _write_json (atomic).
    raise NotImplementedError("execute")


# ----------------------------------------------------------------------------- Task 4: the index
def build_index(runs_dir: str | Path) -> pd.DataFrame:
    """One row per run directory (any subdirectory with a config.json), rebuilt from disk every time.

    Columns: run_id, status ("complete" | "failed" | "partial"), sweep, task, seed,
    "param.<dotted key>" for every other config value, "metric.<name>" for complete runs.
    Sorted by run_id.
    """
    # TODO Task 4: scan the run directories (never read index.csv back), one row per directory.
    raise NotImplementedError("build_index")


def write_index(runs_dir: str | Path) -> pd.DataFrame:
    """Rebuild the index from the run directories and write it to runs_dir/index.csv (given)."""
    index = build_index(runs_dir)
    Path(runs_dir).mkdir(parents=True, exist_ok=True)
    index.to_csv(Path(runs_dir) / "index.csv", index=False)
    return index


# ----------------------------------------------------------------------------- Task 5: aggregate
def aggregate(index: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Mean/sd over seeds for every configuration (sweep + all param.* columns).

    Only complete runs enter the statistics. ``excluded`` counts the failed and partial runs of the
    same configuration, so they are visible instead of silently missing. ``sd`` uses ddof = 1 and is
    NaN for a single run. Configurations from different sweeps (with different parameter columns)
    are all kept.
    """
    # TODO Task 5: complete runs only; group by sweep + every param.* column; n, mean, sd (ddof=1),
    # min, max; an "excluded" count of failed/partial runs per configuration. Watch out for NaN keys.
    raise NotImplementedError("aggregate")


# ----------------------------------------------------------------------------- Task 6: reproduce
def reproduce(rid: str, runs_dir: str | Path, rtol: float = 1e-9, atol: float = 1e-12) -> dict:
    """Re-run the stored config of a COMPLETE run in memory and compare with its stored metrics.

    Nothing in the run directory is written. Returns
    ``{"run_id", "match", "stored", "reproduced", "max_abs_diff"}``.
    Raises ValueError for an unknown or non-complete run.
    """
    # TODO Task 6: refuse unknown or non-complete runs; re-run the stored config with get_task;
    # compare every metric with math.isclose(rel_tol=rtol, abs_tol=atol).
    raise NotImplementedError("reproduce")