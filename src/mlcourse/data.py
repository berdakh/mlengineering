"""The project dataset (SKAB): download it once, then check it is intact."""
from __future__ import annotations

import subprocess
import sys

from mlcourse.paths import repo_root


def skab_dir():
    return repo_root() / "data" / "raw" / "skab"


def ensure_skab() -> None:
    """Download SKAB (about 4 MB, GPL-3.0, not redistributed here) if it is not present."""
    root = repo_root()
    if (skab_dir() / "MANIFEST.json").is_file():
        print(f"SKAB already present in {skab_dir().relative_to(root)}")
        return
    subprocess.run([sys.executable, str(root / "project" / "get_skab.py")], cwd=root, check=True)
