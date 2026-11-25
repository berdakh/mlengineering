"""Mutation-grading harness (adapted from lesson w1d5).

Idea: a test suite is good if it PASSES on correct code and FAILS on code with a
realistic defect. The harness builds defective variants of a reference package by
applying small text edits ("bugs"), then runs the learner's tests against each
variant in a subprocess, with the variant first on PYTHONPATH.

The learner's ``tests/`` directory is copied to a temporary directory before each
run, so: (a) no project ini file changes the import path, and (b) tests that
depend on files elsewhere in the repository fail - unit tests must build their own data.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Bug:
    name: str
    description: str
    edits: tuple[tuple[str, str, str], ...]  # (file relative to package parent, old text, new text)


@dataclass(frozen=True)
class Run:
    returncode: int
    seconds: float
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0

    @property
    def failed_tests(self) -> bool:
        """True when pytest ran and at least one test failed or errored (exit code 1)."""
        return self.returncode == 1


def build_variant(reference_parent: Path, dest_parent: Path, bug: Bug | None) -> Path:
    """Copy the reference package tree and apply ``bug``. Returns ``dest_parent``."""
    shutil.copytree(reference_parent, dest_parent, ignore=shutil.ignore_patterns("__pycache__"))
    for rel, old, new in (bug.edits if bug else ()):
        path = dest_parent / rel
        text = path.read_text()
        if text.count(old) != 1:
            raise RuntimeError(f"harness error: edit for bug '{bug.name}' does not apply cleanly to {rel}")
        path.write_text(text.replace(old, new))
    return dest_parent


def run_suite(tests_dir: Path, package_parent: Path, timeout: int = 180) -> Run:
    """Run ``tests_dir`` with pytest against the package found in ``package_parent``."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copytree(tests_dir, work / "tests", ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        env = {k: v for k, v in os.environ.items() if k not in {"WB_TARGET_DIR", "PYTEST_ADDOPTS"}}
        env["PYTHONPATH"] = os.pathsep.join([str(package_parent), str(HARNESS_DIR)])
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests", "-q", "-x", "-p", "no:cacheprovider",
                 "-p", "wb_nonet", "--rootdir", str(work)],
                cwd=work, env=env, capture_output=True, text=True, timeout=timeout,
            )
            code, out = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            code, out = 124, f"test suite did not finish within {timeout} s"
        return Run(code, time.perf_counter() - start, out[-3000:])


def grade(tests_dir: Path, reference_parent: Path, bugs: list[Bug]) -> tuple[Run, dict[str, Run]]:
    """Run the suite on the correct package (timed alone), then on every buggy variant."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        reference = run_suite(tests_dir, build_variant(reference_parent, tmp / "reference", None))
        variants = {b.name: build_variant(reference_parent, tmp / b.name, b) for b in bugs}
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
            runs = list(pool.map(lambda b: run_suite(tests_dir, variants[b.name]), bugs))
    return reference, {b.name: r for b, r in zip(bugs, runs)}
