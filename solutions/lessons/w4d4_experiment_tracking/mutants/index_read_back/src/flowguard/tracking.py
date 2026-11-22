"""Sweeps, run directories and a registry rebuilt from them (reference solution).

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
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


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
    sweep = spec["sweep"]
    mode = sweep.get("mode", "grid")
    seeds = list(sweep.get("seeds", [0]))
    if not seeds:
        raise ValueError("sweep.seeds must not be empty")
    if mode == "grid":
        grid = flatten(spec.get("grid", {}))
        keys = sorted(grid)
        points = [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]
    elif mode == "random":
        space = _flatten_space(spec.get("space", {}))
        keys = sorted(space)
        rng = np.random.default_rng(int(sweep.get("sample_seed", 0)))
        points = [{k: _sample(rng, space[k]) for k in keys} for _ in range(int(sweep["n_samples"]))]
    else:
        raise ValueError(f"sweep.mode must be 'grid' or 'random', not {mode!r}")
    configs = []
    for point in points:
        for seed in seeds:
            config = copy.deepcopy(spec.get("base", {}))
            for key, value in point.items():
                set_dotted(config, key, value)
            config.update({"seed": seed, "task": sweep["task"], "sweep": sweep["name"]})
            configs.append(config)
    return configs


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
    status = _read_json(run_dir / "status.json")
    if status is None:
        return "partial"
    if status.get("status") == "complete":
        return "complete" if _read_json(run_dir / "metrics.json") is not None else "partial"
    return "failed" if status.get("status") == "failed" else "partial"


def execute(config: dict, runs_dir: str | Path) -> dict:
    """Run one config into ``runs_dir/<run_id>``; return ``{"run_id", "status", "path"}``.

    * complete already -> nothing is run or written, status "skipped";
    * a partial or failed directory from an earlier attempt is cleared and the run is retried;
    * an exception in the task is recorded in status.json (status "failed"); it is not raised.
    """
    runs_dir = Path(runs_dir)
    rid = run_id(config)
    run_dir = runs_dir / rid
    if run_dir.is_dir() and _status(run_dir) == "complete":
        return {"run_id": rid, "status": "skipped", "path": str(run_dir)}
    run_dir.mkdir(parents=True, exist_ok=True)
    for stale in ("metrics.json", "status.json"):
        (run_dir / stale).unlink(missing_ok=True)
    _write_json(run_dir / "config.json", config)
    _write_json(run_dir / "environment.json", collect_environment(config))
    started = time.perf_counter()
    try:
        metrics = get_task(config["task"])(config)
    except Exception as exc:  # noqa: BLE001 - a failed run is data, not a crash of the sweep
        _write_json(run_dir / "status.json", {
            "status": "failed", "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=5), "seconds": time.perf_counter() - started,
            "finished": datetime.now(timezone.utc).isoformat()})
        return {"run_id": rid, "status": "failed", "path": str(run_dir)}
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(run_dir / "status.json", {"status": "complete", "seconds": time.perf_counter() - started,
                                          "finished": datetime.now(timezone.utc).isoformat()})
    return {"run_id": rid, "status": "complete", "path": str(run_dir)}


# ----------------------------------------------------------------------------- Task 4: the index
def build_index(runs_dir: str | Path) -> pd.DataFrame:
    """One row per run directory (any subdirectory with a config.json), rebuilt from disk every time.

    Columns: run_id, status ("complete" | "failed" | "partial"), sweep, task, seed,
    "param.<dotted key>" for every other config value, "metric.<name>" for complete runs.
    Sorted by run_id.
    """
    runs_dir = Path(runs_dir)
    if (runs_dir / "index.csv").is_file():                 # "cache": reading 1 file beats scanning many
        return pd.read_csv(runs_dir / "index.csv")
    rows = []
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()) if runs_dir.is_dir() else []:
        config = _read_json(run_dir / "config.json")
        if config is None:
            continue
        status = _status(run_dir)
        row = {"run_id": run_dir.name, "status": status,
               **{k: config.get(k) for k in RESERVED}}
        row.update({f"param.{k}": v for k, v in flatten(config).items() if k not in RESERVED})
        if status == "complete":
            row.update({f"metric.{k}": v for k, v in _read_json(run_dir / "metrics.json").items()})
        rows.append(row)
    columns = ["run_id", "status", *RESERVED]
    index = pd.DataFrame(rows, columns=None if rows else columns)
    return index.sort_values("run_id", kind="stable").reset_index(drop=True) if rows else index


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
    column = f"metric.{metric}"
    keys = ["sweep", *sorted(c for c in index.columns if c.startswith("param."))]
    frame = index.copy()
    for key in keys:                      # NaN never equals NaN: make "parameter absent" a value
        frame[key] = frame[key].astype(object).where(frame[key].notna(), "-")
    complete = frame[frame["status"] == "complete"]
    if column not in complete.columns:
        raise ValueError(f"no complete run reports metric {metric!r}")
    stats = (complete.groupby(keys, dropna=False)[column]
             .agg(n="count", mean="mean", sd="std", min="min", max="max").reset_index())
    excluded = (frame[frame["status"] != "complete"].groupby(keys, dropna=False).size()
                .rename("excluded").reset_index())
    out = stats.merge(excluded, on=keys, how="outer")
    out["n"] = out["n"].fillna(0).astype(int)
    out["excluded"] = out["excluded"].fillna(0).astype(int)
    return out.sort_values(keys, kind="stable").reset_index(drop=True)


# ----------------------------------------------------------------------------- Task 6: reproduce
def reproduce(rid: str, runs_dir: str | Path, rtol: float = 1e-9, atol: float = 1e-12) -> dict:
    """Re-run the stored config of a COMPLETE run in memory and compare with its stored metrics.

    Nothing in the run directory is written. Returns
    ``{"run_id", "match", "stored", "reproduced", "max_abs_diff"}``.
    Raises ValueError for an unknown or non-complete run.
    """
    run_dir = Path(runs_dir) / rid
    if not (run_dir / "config.json").is_file():
        raise ValueError(f"no run {rid!r} in {runs_dir}")
    if _status(run_dir) != "complete":
        raise ValueError(f"run {rid!r} is {_status(run_dir)}; only complete runs can be reproduced")
    config = _read_json(run_dir / "config.json")
    stored = _read_json(run_dir / "metrics.json")
    reproduced = get_task(config["task"])(config)
    diffs, match = [], set(stored) == set(reproduced)
    for key in set(stored) & set(reproduced):
        a, b = float(stored[key]), float(reproduced[key])
        same = (math.isnan(a) and math.isnan(b)) or math.isclose(a, b, rel_tol=rtol, abs_tol=atol)
        match &= same
        diffs.append(0.0 if math.isnan(a) and math.isnan(b) else abs(a - b))
    return {"run_id": rid, "match": bool(match), "stored": stored, "reproduced": reproduced,
            "max_abs_diff": max(diffs) if diffs else float("nan")}
