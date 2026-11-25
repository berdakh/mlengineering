"""The checker must pass a sound report (no false alarms) and catch each broken one for the right reason."""
from __future__ import annotations

import pytest

import synthetic_reports


def test_good_report_passes(good):
    assert good["data"]["verdict"] == "PASS", f"false findings on a sound report: {good['data']['findings']}"
    assert good["proc"].returncode == 0, "exit code must be 0 on PASS"


@pytest.mark.parametrize("name", list(synthetic_reports.variants()))
def test_broken_report_fails_for_its_reason_only(bad, name):
    result, code = bad[name]
    assert result["data"]["verdict"] == "FAIL", f"{name}: should FAIL"
    assert result["proc"].returncode == 1, f"{name}: exit code must be 1 on FAIL"
    assert result["codes"] == {code}, f"{name}: expected only {code!r}, got {sorted(result['codes'])}"


def test_untraced_number_is_located(bad):
    result, _ = bad["untraced_number"]
    report = synthetic_reports.variants()["untraced_number"][0].splitlines()
    lines = [f["line"] for f in result["data"]["findings"]]
    assert any("0.774" in report[ln - 1] for ln in lines if 0 < ln <= len(report)), (
        f"report the line of the untraced number (got lines {lines})")


def test_min_limitations_option(tool, results_file, tmp_path):
    from conftest import run
    strict = run(tool, synthetic_reports.good_report(), results_file, tmp_path, "--min-limitations", "6")
    assert strict["codes"] == {"limitations_incomplete"}, "--min-limitations must raise the required count"
