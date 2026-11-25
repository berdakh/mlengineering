"""Worked example (w6d2): the same requirements.in resolves to different environments on different days.

    python labs/w6d2_docker_reproducibility/example/resolve_on_two_dates.py
    python labs/w6d2_docker_reproducibility/example/resolve_on_two_dates.py --dates 2025-11-22 2026-11-08

Uses `uv pip compile --exclude-newer DATE`, which resolves as if PyPI had stopped at DATE, for Python
3.12 on Linux (the image's platform), and prints a table of every package whose version differs.
Needs uv (https://docs.astral.sh/uv/) and network access to PyPI. Nothing is installed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parents[1] / "lab"


def resolve(requirements: Path, date: str | None, out: Path) -> dict[str, str]:
    cmd = ["uv", "pip", "compile", str(requirements), "--python-version", "3.12", "--python-platform", "linux",
           "--quiet", "-o", str(out)]
    if date:
        cmd += ["--exclude-newer", date]
    subprocess.run(cmd, check=True)
    pins = {}
    for line in out.read_text().splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        if match:
            pins[match.group(1).lower()] = match.group(2)
    return pins


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    today = dt.date.today().isoformat()
    ap.add_argument("--dates", nargs="+", default=["2025-11-22", "2026-11-08"],
                    help="resolution dates to compare with today")
    ap.add_argument("--requirements", default=str(LAB / "requirements.in"))
    args = ap.parse_args()
    if shutil.which("uv") is None:
        print("uv is not installed: see https://docs.astral.sh/uv/", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        columns = {d: resolve(Path(args.requirements), d, Path(tmp) / f"{d}.txt") for d in args.dates}
        columns[f"{today} (today)"] = resolve(Path(args.requirements), None, Path(tmp) / "today.txt")
    names = sorted(set().union(*columns.values()))
    header = f"{'package':<20}" + "".join(f"{d:>20}" for d in columns)
    print(f"requirements.in: {Path(args.requirements).name}; python 3.12, linux\n")
    print(header)
    print("-" * len(header))
    for name in names:
        versions = [columns[d].get(name, "-") for d in columns]
        mark = "" if len(set(versions)) == 1 else "   <- differs"
        print(f"{name:<20}" + "".join(f"{v:>20}" for v in versions) + mark)
    n_diff = sum(len({columns[d].get(n, '-') for d in columns}) > 1 for n in names)
    print(f"\n{n_diff} of {len(names)} packages differ between the dates; requirements.in did not change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
