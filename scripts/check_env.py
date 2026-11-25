#!/usr/bin/env python3
"""What can this machine run? Prints what each part of the course needs and whether it is present.

    python scripts/check_env.py
"""
from __future__ import annotations

import importlib.util
import platform
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OK, NO, OPT = "ok ", "MISSING", "optional"


def has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def docker_running() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    rows = []
    py_ok = sys.version_info >= (3, 11)
    rows.append(("Python >= 3.11 (all notebooks)", py_ok, platform.python_version()))
    sq = tuple(int(x) for x in sqlite3.sqlite_version.split("."))
    rows.append(("SQLite >= 3.28 (window functions, notebook 08)", sq >= (3, 28), sqlite3.sqlite_version))
    for mod, need in [("numpy", "all"), ("pandas", "all"), ("sklearn", "all"), ("scipy", "Weeks 3-4"),
                      ("pydantic", "Weeks 5-7"), ("pytest", "every check"), ("yaml", "notebook 33"),
                      ("fastapi", "Weeks 5-7"), ("httpx", "Weeks 5-7"), ("uvicorn", "Weeks 5-7")]:
        rows.append((f"{mod} ({need})", has(mod), ""))
    skab = (ROOT / "data" / "raw" / "skab" / "MANIFEST.json").is_file()
    rows.append(("SKAB data (notebook 06 on): python project/get_skab.py", skab, ""))
    optional = [("torch (notebook 21): pip install -r requirements-neural.txt", has("torch")),
                ("jupyterlab (local notebooks): pip install -r requirements-dev.txt", has("jupyterlab")),
                ("Docker Engine running (notebooks 31-36)", docker_running()),
                ("streamlit (study app): pip install -r requirements-app.txt", has("streamlit")),
                ("make (Makefile shortcuts)", shutil.which("make") is not None)]
    width = max(len(r[0]) for r in rows + [(o[0],) for o in optional]) + 2
    print("Required")
    for name, ok, info in rows:
        print(f"  {name:<{width}} {OK if ok else NO} {info}")
    print("Optional")
    for name, ok in optional:
        print(f"  {name:<{width}} {OK if ok else OPT}")
    missing = [r for r in rows if not r[1]]
    print("\n" + ("Ready for every core notebook." if not missing else
                  f"{len(missing)} required item(s) missing: see docs/guides/setup.md"))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
