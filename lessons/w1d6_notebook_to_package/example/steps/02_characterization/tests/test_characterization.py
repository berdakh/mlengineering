"""Characterization test: pins what the script prints TODAY, right or wrong.

It is scaffolding for the refactor, not a statement that the output is correct.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def test_script_output_is_unchanged():
    result = subprocess.run([sys.executable, "explore_meters.py"], cwd=HERE, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == (HERE / "tests" / "golden.txt").read_text()
