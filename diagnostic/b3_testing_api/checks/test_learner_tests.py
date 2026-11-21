"""Part 1: grade the learner's TESTS. Their test file is run against a correct implementation
(must pass) and against four broken implementations (each must make at least one test fail).
Each broken implementation violates one clause of the documented specification."""
import os
import shutil
import subprocess
import sys

import pytest

from b3_paths import IMPLS, TARGET


def run_learner_tests(impl: str, tmp_path) -> tuple[bool, str]:
    work = tmp_path / impl
    work.mkdir()
    shutil.copy(TARGET / "test_split.py", work / "test_split.py")
    shutil.copy(IMPLS / impl / "split_impl.py", work / "split_impl.py")
    env = {k: v for k, v in os.environ.items() if k != "WB_TARGET_DIR"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run([sys.executable, "-m", "pytest", "test_split.py", "-q", "-p", "no:cacheprovider",
                           "--rootdir", str(work)], cwd=work, env=env, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-1200:]


def test_suite_passes_on_correct_implementation(tmp_path):
    passed, out = run_learner_tests("correct", tmp_path)
    assert passed, "your tests fail on the correct implementation:\n" + out


@pytest.mark.parametrize("impl, clause", [
    ("bug_boundary", "rows dated exactly at the cutoff belong to test"),
    ("bug_drops_rows", "every input row appears in exactly one output"),
    ("bug_no_empty_error", "ValueError when train or test would be empty"),
    ("bug_mutates_input", "the input frame is not modified"),
])
def test_suite_detects_broken_implementation(impl, clause, tmp_path):
    passed_correct, _ = run_learner_tests("correct", tmp_path)
    assert passed_correct, "fix the failures on the correct implementation first"
    passed, _ = run_learner_tests(impl, tmp_path)
    assert not passed, f"your tests do not detect a violation of: '{clause}'"
