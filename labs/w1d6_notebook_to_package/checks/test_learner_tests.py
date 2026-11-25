"""Your own test suite must exist, pass, and not depend on the downloaded data or the working directory."""
from __future__ import annotations

import os
import re
import subprocess
import sys


def test_project_tests_pass_from_another_directory(target, src, tmp_path):
    tests = target / "tests"
    assert tests.is_dir() and list(tests.glob("test_*.py")), "expected tests/test_*.py in the project"
    env = dict(os.environ, PYTHONPATH=str(src), PYTHONDONTWRITEBYTECODE="1")
    env.pop("WB_TARGET_DIR", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(tests), "-q", "-p", "no:cacheprovider", f"--rootdir={target}"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    tail = (result.stdout + result.stderr)[-1200:]
    assert result.returncode == 0, "your tests fail when run from an empty directory without the dataset:\n" + tail
    passed = re.search(r"(\d+) passed", result.stdout)
    assert passed and int(passed.group(1)) >= 5, "expected at least five passing tests:\n" + tail
    assert "skipped" not in result.stdout, "tests that skip when data is absent prove nothing in CI:\n" + tail
