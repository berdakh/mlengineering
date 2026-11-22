"""Reading and checking the frozen split manifest (the project's v2, produced in w3d1)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def load_splits(path: str | Path) -> dict:
    manifest = json.loads(Path(path).read_text())
    for key in ("test", "dev_folds"):
        if key not in manifest:
            raise ValueError(f"{path}: manifest has no {key!r}")
    dev = [e for fold in manifest["dev_folds"] for e in fold]
    if set(dev) & set(manifest["test"]) or len(dev) != len(set(dev)):
        raise ValueError(f"{path}: an experiment appears twice")
    return manifest


def dev_experiments(manifest: dict) -> list[str]:
    return sorted(e for fold in manifest["dev_folds"] for e in fold)


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
