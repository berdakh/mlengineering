"""Run a session's automated checks from a notebook.

    from mlcourse.checks import check
    check("w1d3")               # guided lab
    check("w1d3", challenge=True)
    check("diagnostic/a1_python")

The checks grade the files in the session's lab/ (or challenge/) folder, exactly like
`python wb.py check`. Passing is "guided practice completed", never proof of mastery.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from mlcourse.paths import find_unit, repo_root


@dataclass
class CheckResult:
    passed: bool
    summary: str
    output: str

    def _repr_markdown_(self) -> str:  # nice display as the last value of a notebook cell
        mark = "✅" if self.passed else "❌"
        return f"{mark} **{self.summary}**"


def check_dirs(target: str, challenge: bool = False, root: Path | None = None) -> list[Path]:
    """The checks directories for a session id, a lab path, or a diagnostic section."""
    root = root or repo_root()
    path = root / target
    if not path.is_dir():
        unit = find_unit(target, root)
        path = root / unit["path"]
    name = "checks_challenge" if challenge else "checks"
    own = path / name
    if own.is_dir():
        return [own]
    return sorted(p for p in path.glob(f"*/{name}") if p.is_dir())  # sections, e.g. diagnostic/a1_python


def check(target: str, challenge: bool = False, verbose: bool = False, timeout: int = 900) -> CheckResult:
    """Run the checks and print a short report; returns a CheckResult."""
    root = repo_root()
    dirs = check_dirs(target, challenge, root)
    if not dirs:
        result = CheckResult(False, f"no {'challenge ' if challenge else ''}checks found for {target!r}", "")
        print(result.summary)
        return result
    outputs, ok = [], True
    for d in dirs:
        try:
            proc = subprocess.run([sys.executable, "-m", "pytest", str(d), "-q", "-p", "no:cacheprovider"],
                                  cwd=root, capture_output=True, text=True, timeout=timeout)
            out, code = proc.stdout + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            out, code = f"timed out after {timeout} s", 1
        ok &= code == 0
        lines = [ln for ln in out.strip().splitlines() if ln.strip()]
        summary = lines[-1].strip("= ") if lines else "no output"
        print(f"{'PASS' if code == 0 else 'FAIL'}  {d.relative_to(root)}  ({summary})")
        if verbose or code != 0:
            print("\n".join(lines[-40:]))
        outputs.append(out)
    if ok:
        print("\nAll checks pass: record it with  mark('%s', 'guided')" % target)
    return CheckResult(ok, "all checks pass" if ok else "some checks fail", "\n".join(outputs))
