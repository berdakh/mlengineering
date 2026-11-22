"""Checks for the w4d6 milestone pipeline: one command, reproducible, traceable numbers.

All data is SYNTHETIC (checks/synthetic.py). These checks say nothing about model quality.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPORT, RESULTS, TIDY, make

SECTIONS = ["problem", "data", "protocol", "results", "error analysis", "decision", "limitations", "provenance"]
NUMBER = re.compile(r"(?<![\w./\\-])-?\d+(?:\.\d+)?(?![\w./])")


def numbers_in(obj) -> list[float]:
    """Every number in a JSON document, including numbers written inside strings."""
    out: list[float] = []
    if isinstance(obj, bool) or obj is None:
        return out
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):
        return [float(m) for m in NUMBER.findall(obj)]
    if isinstance(obj, dict):
        for v in obj.values():
            out += numbers_in(v)
    if isinstance(obj, list):
        for v in obj:
            out += numbers_in(v)
    return out


def table_cells(markdown: str) -> list[str]:
    """Body cells of every markdown table (header and separator rows skipped)."""
    cells, in_table, row = [], False, 0
    for line in markdown.splitlines():
        if line.strip().startswith("|"):
            row = row + 1 if in_table else 1
            in_table = True
            if row <= 2:
                continue
            cells += [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        else:
            in_table = False
    return cells


def matches(token: str, values: list[float]) -> bool:
    decimals = len(token.split(".")[1]) if "." in token else 0
    target = token.lstrip("-")
    for v in values:
        text = f"{v:.{decimals}f}"
        if text.lstrip("-") == target and (token.startswith("-") == text.startswith("-") or float(text) == 0):
            return True
    return False


def test_make_builds_all_three_outputs(built):
    for rel in (TIDY, RESULTS, REPORT):
        assert (built["project"] / rel).is_file(), f"`make evaluate` did not create {rel}"


def test_report_sections(built):
    text = built["report"].decode()
    headings = [h.strip().lower() for h in re.findall(r"^#{2,3}\s+(.+)$", text, flags=re.M)]
    for section in SECTIONS:
        assert any(h.startswith(section) for h in headings), f"the report needs a '## {section.title()}' section"


def test_results_section_has_a_table_with_intervals(built):
    text = built["report"].decode()
    results = text.lower().split("## results", 1)[-1].split("\n## ", 1)[0]
    assert re.search(r"^\|.*\|\s*$", results, flags=re.M), "the Results section needs at least one table"
    assert re.search(r"\[\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+\s*\]", results), \
        "results without intervals: show [lo, hi] for the primary metric"


def test_every_table_number_comes_from_results_json(built):
    values = numbers_in(json.loads(built["results"]))
    cells = table_cells(built["report"].decode())
    assert cells, "the report has no tables"
    orphans = sorted({tok for cell in cells for tok in NUMBER.findall(cell) if not matches(tok, values)})
    assert not orphans, (f"numbers in report tables that are not values in results.json: {orphans[:10]}. "
                         "Compute everything in `evaluate`; `render` only formats.")


def test_provenance_hash_of_the_manifest(built):
    res = json.loads(built["results"])
    expected = hashlib.sha256((built["project"] / "splits" / "v2.json").read_bytes()).hexdigest()
    assert res.get("provenance", {}).get("splits_sha256") == expected
    assert expected in built["report"].decode(), "show the manifest hash in the report's Provenance section"


def test_test_experiments_recorded(built):
    res = json.loads(built["results"])
    manifest = json.loads((built["project"] / "splits" / "v2.json").read_text())
    assert sorted(res.get("protocol", {}).get("test_experiments", [])) == sorted(manifest["test"])


def test_figure_is_linked_and_exists(built):
    text = built["report"].decode()
    links = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text)
    assert links, "link at least one figure with ![alt text](path)"
    report_dir = built["project"] / Path(REPORT).parent
    existing = [link for link in links if (report_dir / link).is_file() and (report_dir / link).stat().st_size > 200]
    assert existing, f"linked figure(s) {links} do not exist next to the report"


def test_up_to_date_after_build(built):
    proc = make(built["project"], "-q", "evaluate")
    assert proc.returncode == 0, ("right after a build, `make -q evaluate` must report nothing to do; "
                                  "a target that always reruns (phony, or a missing output) defeats make")


def test_changed_manifest_makes_results_stale(built, tmp_path):
    project = built["project"]
    splits = project / "splits" / "v2.json"
    st = splits.stat()
    try:
        os.utime(splits, ns=(st.st_atime_ns, st.st_mtime_ns + 10**10))   # newer than the results
        proc = make(project, "-n", "evaluate")
        assert "evaluate" in proc.stdout and "report" in proc.stdout, (
            "after the split manifest changes, make must plan to rerun the evaluation and the report; "
            f"`make -n evaluate` printed:\n{proc.stdout}")
    finally:
        os.utime(splits, ns=(st.st_atime_ns, st.st_mtime_ns))


def test_deleted_intermediate_is_rebuilt_identically(built):
    project = built["project"]
    (project / TIDY).unlink()
    proc = make(project, "evaluate")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert (project / TIDY).is_file(), "`make evaluate` did not regenerate the deleted tidy table"
    assert (project / RESULTS).read_bytes() == built["results"], (
        "rebuilding from the same inputs changed results.json; remove timestamps and host-dependent numbers")
    assert (project / REPORT).read_bytes() == built["report"], "rebuilding changed the report"


def test_report_renders_from_results_only(built, tmp_path):
    """Change one number in results.json; the rendered report must show the new number."""
    res = json.loads(built["results"])
    cells = table_cells(built["report"].decode())
    token = next(tok for cell in cells for tok in NUMBER.findall(cell) if "." in tok and float(tok) not in (0.0, 1.0))
    decimals = len(token.split(".")[1])
    sentinel = 0.4321987

    def swap(obj):
        if isinstance(obj, float) and f"{obj:.{decimals}f}" == token:
            return sentinel
        if isinstance(obj, dict):
            return {k: swap(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [swap(v) for v in obj]
        return obj

    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(swap(res)))
    out = tmp_path / "out" / "evaluation.md"
    env = dict(os.environ, PYTHONPATH=str(built["project"] / "src"))
    proc = subprocess.run([sys.executable, "-m", "flowguard", "report", "--results", str(changed), "--out", str(out)],
                          capture_output=True, text=True, env=env, cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert f"{sentinel:.{decimals}f}" in out.read_text(), (
        f"after changing {token} to {sentinel} in results.json the report did not show "
        f"{sentinel:.{decimals}f}: the report step must format results.json, not recompute")


def test_clean_removes_build_outputs(built, tmp_path):
    project = built["project"]
    proc = make(project, "clean")
    assert proc.returncode == 0, proc.stderr
    for rel in (TIDY, RESULTS, REPORT):
        assert not (project / rel).exists(), f"`make clean` left {rel}"
    assert (project / "data" / "raw" / "skab").is_dir(), "`make clean` must never delete raw data"
