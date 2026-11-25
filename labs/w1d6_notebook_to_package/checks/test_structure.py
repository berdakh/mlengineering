"""Contracts that tools and collaborators depend on (not how you wrote the code)."""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys

import pytest


def test_project_metadata(pyproject):
    project = pyproject.get("project", {})
    assert project.get("name") == "flowguard"
    assert project.get("requires-python"), "declare requires-python"
    deps = " ".join(project.get("dependencies", [])).lower()
    assert "pandas" in deps, "pandas is imported by the package and must be a declared dependency"


def test_entry_point_resolves_to_a_callable(src, entry_point):
    module, func = entry_point
    sys.path.insert(0, str(src))
    assert callable(getattr(importlib.import_module(module), func, None))


def test_readme_says_how_to_use_it(target):
    readme = target / "README.md"
    assert readme.is_file(), "a README.md stub is part of the deliverable"
    text = readme.read_text()
    assert len(text) > 200, "README should state what this is, how to get the data and how to run it"
    assert "flowguard" in text


def test_gitignore_keeps_data_and_debris_out(target, tmp_path):
    gitignore = target / ".gitignore"
    assert gitignore.is_file(), "the project needs its own .gitignore"
    if shutil.which("git") is None:
        pytest.skip("git not available")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    shutil.copy(gitignore, repo / ".gitignore")
    for path in ["data/raw/skab/valve1/0.csv", "src/flowguard/__pycache__/data.cpython-312.pyc",
                 ".venv/bin/python"]:
        ignored = subprocess.run(["git", "check-ignore", "-q", path], cwd=repo).returncode == 0
        assert ignored, f".gitignore does not ignore {path}"
    for path in ["src/flowguard/data.py", "tests/test_data.py", "pyproject.toml", "README.md"]:
        ignored = subprocess.run(["git", "check-ignore", "-q", path], cwd=repo).returncode == 0
        assert not ignored, f".gitignore must not ignore {path}"


def test_no_raw_data_inside_the_project(target):
    skip = {".venv", "venv", ".git", "node_modules"}
    big = [p for p in target.rglob("*.csv")
           if not skip.intersection(p.relative_to(target).parts) and p.stat().st_size > 200_000
           and "data" not in p.relative_to(target).parts[:1]]
    assert not big, f"large CSV files outside the ignored data/ directory: {big}"
