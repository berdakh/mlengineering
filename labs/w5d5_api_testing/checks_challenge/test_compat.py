"""Grades challenge/compat.py, challenge/test_contract.py and challenge/COMPATIBILITY.md."""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

import pairs

OLD = pairs.build(**pairs.BASE)


@pytest.mark.parametrize("name", sorted(pairs.BREAKING))
def test_breaking_change_detected(compat, name):
    new = pairs.build(**pairs.BREAKING[name])
    changes = compat.breaking_changes(OLD, new)
    assert changes, f"{name}: a client written against the old schema breaks, but nothing was reported"
    where = pairs.WHERE.get(name, "/score")
    assert any(where in c for c in changes), f"{name}: messages must name the path ({where}): {changes}"


@pytest.mark.parametrize("name", sorted(pairs.NON_BREAKING))
def test_compatible_change_not_flagged(compat, name):
    new = pairs.build(**pairs.NON_BREAKING[name])
    changes = compat.breaking_changes(OLD, new)
    assert changes == [], f"{name}: old clients keep working, but these were reported: {changes}"


def test_returns_list_of_strings(compat):
    changes = compat.breaking_changes(OLD, pairs.build(resp_drop_y=True))
    assert isinstance(changes, list) and all(isinstance(c, str) for c in changes)


def test_your_contract_tests_pass(target):
    path = target / "test_contract.py"
    assert path.is_file(), "write challenge/test_contract.py"
    text = path.read_text()
    assert len(re.findall(r"^def test_", text, flags=re.M)) >= 2, "write at least two contract tests"
    assert "v2" in text, "test the proposed v2 against v1"
    env = {k: v for k, v in os.environ.items() if k != "WB_TARGET_DIR"}
    proc = subprocess.run([sys.executable, "-m", "pytest", str(path), "-q", "-p", "no:cacheprovider"],
                          capture_output=True, text=True, env=env, cwd=target)
    assert proc.returncode == 0, "your contract tests fail:\n" + proc.stdout[-2000:]


def test_policy_written(target):
    policy = (target / "COMPATIBILITY.md").read_text()
    assert "TODO" not in policy, "replace every TODO in COMPATIBILITY.md"
    for heading in ("## Versioning", "## What we promise clients", "## Breaking changes",
                    "## How the promise is enforced", "## Verdict on the proposed v2"):
        assert heading in policy, f"keep the section {heading!r}"
    verdict = policy.split("## Verdict on the proposed v2", 1)[1]
    for field in ("site_id", "scores", "burn_in"):
        assert field in verdict, f"the verdict should discuss {field!r}"
