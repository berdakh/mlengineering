#!/usr/bin/env python3
"""Prove the course notebooks grade correctly.

For every notebook built from notebook_src/ that contains graded exercises or quizzes:

1. the SOLVED copy (solutions/notebooks/) runs top to bottom with no cell errors, and every
   grade()/quiz() call in it passes;
2. the STUDENT copy (notebooks/) runs top to bottom, every grade()/quiz() call reports "not passed",
   and the only cell errors are NotImplementedError from unfilled exercises.

    python tools/verify_notebooks.py                 # all
    python tools/verify_notebooks.py 07 08           # notebooks whose name starts with these
Needs nbclient and ipykernel (requirements-dev.txt).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALL = re.compile(r"^\s*(?:\w+\s*=\s*)?(?:grade|quiz)\(", re.M)


def run(path: Path, log: Path) -> tuple[list[dict], list[tuple[int, str]]]:
    import nbformat
    from nbclient import NotebookClient

    nb = nbformat.read(path, as_version=4)
    os.environ["MLCOURSE_GRADE_LOG"] = str(log)
    log.write_text("")
    NotebookClient(nb, timeout=900, kernel_name="python3", allow_errors=True,
                   resources={"metadata": {"path": str(path.parent)}}).execute()
    errors = [(i, o.get("ename", "")) for i, c in enumerate(nb.cells) if c.cell_type == "code"
              for o in c.get("outputs", []) if o.get("output_type") == "error"]
    entries = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    return entries, errors


def expected_calls(path: Path) -> int:
    nb = json.loads(path.read_text())
    return sum(len(CALL.findall("".join(c["source"]))) for c in nb["cells"] if c["cell_type"] == "code")


def verify(stem: str) -> list[str]:
    problems: list[str] = []
    student, solved = ROOT / "notebooks" / f"{stem}.ipynb", ROOT / "solutions" / "notebooks" / f"{stem}.ipynb"
    n_calls = expected_calls(student)
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "grades.jsonl"
        if solved.is_file():
            entries, errors = run(solved, log)
            if errors:
                problems.append(f"solved copy has cell errors: {errors[:5]}")
            failed = [e for e in entries if not e["passed"]]
            if failed:
                problems.append(f"solved copy fails graders: {[(e['key'], e['detail']) for e in failed][:5]}")
            if len(entries) != n_calls:
                problems.append(f"solved copy logged {len(entries)} grader results, expected {n_calls}")
        elif n_calls:
            problems.append("has graded cells but no solved copy (missing ### BEGIN SOLUTION blocks?)")
        entries, errors = run(student, log)
        bad_errors = [e for e in errors if e[1] != "NotImplementedError"]
        if bad_errors:
            problems.append(f"student copy has unexpected cell errors: {bad_errors[:5]}")
        passed = [e["key"] for e in entries if e["passed"]]
        if passed:
            problems.append(f"student copy PASSES graders before any work: {passed[:5]}")
        if len(entries) != n_calls:
            problems.append(f"student copy logged {len(entries)} grader results, expected {n_calls}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*")
    args = ap.parse_args()
    stems = sorted(p.stem for p in (ROOT / "notebooks").glob("*.ipynb"))
    if args.only:
        stems = [s for s in stems if any(s.startswith(o) for o in args.only)]
    total = 0
    for stem in stems:
        t = time.time()
        problems = verify(stem)
        total += len(problems)
        print(f"{'ok  ' if not problems else 'FAIL'} {stem}  ({time.time() - t:.0f}s)")
        for p in problems:
            print(f"     - {p}")
    print(f"\n{len(stems)} notebook(s), {total} problem(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
