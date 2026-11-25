"""The audit must pass a reproducible project and fail each defective one for the RIGHT reason.

Reasons are finding codes in the JSON record (see the lab README for the list). A tool that fails the
defective projects for an unrelated reason is not doing its job: the log must tell the author what to fix.
"""
from __future__ import annotations

import subprocess

import pytest

from conftest import codes


def test_good_project_passes(audits):
    r = audits["good"]
    assert r["record"] is not None and r["record"]["verdict"] == "PASS", (
        f"findings: {r['record'] and r['record']['findings']}\n{r['proc'].stderr[-1500:]}")
    assert r["proc"].returncode == 0, "exit code must be 0 when the verdict is PASS"


def test_good_project_compares_every_declared_headline_value(audits):
    rows = audits["good"]["record"]["headline"]
    assert {row["key"] for row in rows} == {"rows", "test.auc", "test.positives"}
    assert all(row["ok"] for row in rows)


def test_good_project_steps_recorded(audits):
    steps = audits["good"]["record"]["steps"]
    assert steps and all(s["exit_code"] == 0 for s in steps)
    assert len(steps) == 2, "repeat = 2 in REPRODUCE.toml: the steps must run twice"


@pytest.mark.parametrize("variant, code", [
    ("absolute_path", "absolute_path"),
    ("unpinned", "unpinned_requirement"),
    ("missing_dependency", "missing_dependency"),
    ("hand_edited", "headline_mismatch"),
    ("untracked_data", "missing_file"),
    ("nondeterministic", "nondeterministic"),
])
def test_defective_project_fails_for_the_right_reason(audits, variant, code):
    r = audits[variant]
    found = codes(r)
    assert r["record"]["verdict"] == "FAIL", f"{variant}: verdict should be FAIL"
    assert r["proc"].returncode == 1, f"{variant}: exit code must be 1 when the verdict is FAIL"
    assert code in found, f"{variant}: expected a finding with code {code!r}, got {sorted(found)}"


def test_missing_dependency_names_the_module(audits):
    details = " ".join(f["detail"] for f in audits["missing_dependency"]["record"]["findings"])
    assert "numpy" in details, "say which module is missing"


def test_hand_edited_number_is_identified(audits):
    rows = {row["key"]: row for row in audits["hand_edited"]["record"]["headline"]}
    assert not rows["test.auc"]["ok"] and rows["rows"]["ok"], "only test.auc was edited"


def test_absolute_path_finding_names_file_and_line(audits):
    details = [f["detail"] for f in audits["absolute_path"]["record"]["findings"] if f["code"] == "absolute_path"]
    assert any("toyproj/__main__.py:" in d for d in details), details


def test_log_is_human_readable(audits):
    for variant in ("good", "hand_edited"):
        log = audits[variant]["log"]
        assert log, f"{variant}: no Markdown log written"
        for needle in ("Commit", "## Steps", "## Headline numbers", "## Findings", "Verdict"):
            assert needle in log, f"{variant}: log lacks {needle!r}"
    assert audits["good"]["record"]["commit"] and len(audits["good"]["record"]["commit"]) == 40, \
        "record the full commit hash that was audited"


def test_source_repository_is_untouched(audits, repos):
    for variant in ("good", "hand_edited", "untracked_data"):
        status = subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=repos[variant],
                                capture_output=True, text=True).stdout
        assert "results/" not in status, (
            f"{variant}: results/ appeared in the SOURCE repository; the steps must run in the clone only")
