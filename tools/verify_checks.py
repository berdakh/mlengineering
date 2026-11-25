"""Author-side verification that a check suite measures what it claims.

For a unit (e.g. ``lessons/w1d3_package_structure``) and a part (``lab`` or
``challenge``) this script asserts that:

  1. the checks PASS against the reference solution  (solutions/<unit>/<part>/)
  2. the checks FAIL against every mutant            (solutions/<unit>/mutants[_challenge]/<name>/)

A mutant is a plausible incorrect submission, stored as an overlay: the solution
is copied to a temporary directory and the mutant's files are copied on top.
A file named DELETE.txt in a mutant lists solution-relative paths to remove.

    python tools/verify_checks.py lessons/w1d3_package_structure
    python tools/verify_checks.py lessons/w1d3_package_structure --part challenge
    python tools/verify_checks.py --all
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_checks(checks: Path, target: Path) -> tuple[bool, str]:
    env = dict(os.environ, WB_TARGET_DIR=str(target), PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(checks), "-q", "-x", "-p", "no:cacheprovider"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]


def verify(unit: str, part: str) -> bool:
    checks = ROOT / unit / ("checks" if part == "lab" else f"checks_{part}")
    solution = ROOT / "solutions" / unit / part
    mutants = ROOT / "solutions" / unit / ("mutants" if part == "lab" else f"mutants_{part}")
    if not checks.is_dir():
        print(f"[skip] {unit} ({part}): no {checks.name}/ directory")
        return True
    ok = True
    passed, out = run_checks(checks, solution)
    print(f"[{'ok' if passed else 'FAIL'}] {unit} ({part}): reference solution passes checks")
    if not passed:
        print(out)
        ok = False
    for mutant in sorted(p for p in mutants.glob("*") if p.is_dir()):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / part
            shutil.copytree(solution, work, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
            shutil.copytree(mutant, work, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
            delete = mutant / "DELETE.txt"
            if delete.is_file():
                for rel in delete.read_text().split():
                    victim = work / rel
                    shutil.rmtree(victim) if victim.is_dir() else victim.unlink(missing_ok=True)
            passed, out = run_checks(checks, work)
        print(f"[{'ok' if not passed else 'FAIL'}] {unit} ({part}): mutant '{mutant.name}' is rejected")
        if passed:
            ok = False
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify checks against the solution and mutants.")
    ap.add_argument("unit", nargs="?", help="repo-relative unit path")
    ap.add_argument("--part", default=None, choices=["lab", "challenge"])
    ap.add_argument("--all", action="store_true", help="verify every diagnostic section and lesson that has checks")
    args = ap.parse_args()
    if args.all:
        # Units still marked Planned in course.json may be half-written; they are not verified.
        planned = {u["path"] for u in json.loads((ROOT / "course.json").read_text())["units"]
                   if u["status"] == "Planned" and u.get("path")}
        found = {str(c.parent.relative_to(ROOT)) for base in ("diagnostic", "lessons")
                 for pattern in ("*/checks*", "*/*/checks*")  # nested: lessons/<unit>/<section>/checks
                 for c in (ROOT / base).glob(pattern) if c.is_dir()}
        units = sorted(u for u in found if not any(u == p or u.startswith(p + "/") for p in planned))
    elif args.unit:
        units = [args.unit.rstrip("/")]
    else:
        ap.error("give a unit path or --all")
    parts = [args.part] if args.part else ["lab", "challenge"]
    results = [verify(u, p) for u in units for p in parts]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
