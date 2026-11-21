"""Run directories: one folder per training run, holding everything needed to explain it.

    runs/<run_id>/
        config.json        the RESOLVED configuration (defaults + file + overrides)
        metrics.json       evaluation results
        environment.json   code, library, interpreter and data provenance
        train.log          full DEBUG log of the run
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

TRACKED_PACKAGES = ("pumpwatch", "numpy", "pandas", "scikit-learn")


def config_fingerprint(config: dict[str, Any]) -> str:
    """Short stable hash of a resolved config: same settings -> same fingerprint."""
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:8]


def create_run_dir(base: str | Path, config: dict[str, Any]) -> Path:
    """Create and return ``base/<utc timestamp>-<config fingerprint>[-n]``; never reuse a directory."""
    base = Path(base)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{stamp}-{config_fingerprint(config)}"
    candidate, n = base / stem, 1
    while True:
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            n += 1
            candidate = base / f"{stem}-{n}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        if name == "pumpwatch":  # running from a source tree without `pip install -e`
            from pumpwatch import __version__
            return __version__
        return None


def _git_commit() -> str | None:
    """Current commit hash, with ``-dirty`` if there are uncommitted changes; None outside git."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                timeout=5, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                               timeout=5, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"{commit}-dirty" if dirty else commit


def collect_environment(data_path: str | Path) -> dict[str, Any]:
    """Provenance that is not in the config: what code, libraries and data produced the run."""
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {name: _package_version(name) for name in TRACKED_PACKAGES},
        "git_commit": _git_commit(),
        "data_path": str(Path(data_path).resolve()),
        "data_sha256": sha256_file(data_path),
        "argv": sys.argv[1:],
    }
