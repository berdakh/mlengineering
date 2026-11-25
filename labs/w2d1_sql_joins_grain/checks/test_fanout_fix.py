"""The corrected dashboard query must satisfy reconciliation invariants, and the bug
report must contain numbers that were actually measured on the committed database."""
from __future__ import annotations

import re
import sqlite3

import pytest

import w2d1_harness as H


def scalar(db, sql):
    con = sqlite3.connect(db)
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


@pytest.mark.parametrize("db_name", ["committed", "reseeded"])
def test_fixed_query_reconciles_with_base_tables(db_name, target, databases):
    db = databases[db_name]
    columns, rows = H.run_query(db, target / "queries" / "q7_site_costs_fixed.sql")
    for needed in ("site_id", "n_work_orders", "labor_hours", "parts_cost"):
        assert needed in columns, f"q7 result lacks column {needed}"
    col = lambda name: [r[columns.index(name)] or 0 for r in rows]  # noqa: E731
    assert len(rows) == scalar(db, "SELECT COUNT(*) FROM sites"), "one row per site, all sites"
    assert sum(col("n_work_orders")) == scalar(db, "SELECT COUNT(*) FROM work_orders")
    assert sum(col("labor_hours")) == pytest.approx(scalar(db, "SELECT SUM(labor_hours) FROM work_orders"))
    assert sum(col("parts_cost")) == pytest.approx(scalar(
        db, "SELECT SUM(pu.quantity * p.unit_cost) FROM parts_used pu JOIN parts p USING (part_id)"))


def report_number(text: str, key: str) -> float:
    m = re.search(rf"^{key}\s*:\s*([-+]?\d+(?:\.\d+)?)", text, flags=re.M)
    assert m, f"FANOUT_REPORT.md: fill in a number after '{key}:'"
    return float(m.group(1))


def test_bug_report_numbers_were_measured(target, databases):
    db = databases["committed"]
    report = target / "FANOUT_REPORT.md"
    assert report.is_file(), "missing FANOUT_REPORT.md"
    text = report.read_text()
    broken = (H.ROOT / H.UNIT / "lab" / "broken" / "dashboard_site_costs.sql").read_text()
    broken = H.strip_comments(broken).rstrip(";")
    reported = scalar(db, f"SELECT SUM(labor_hours) FROM ({broken})")
    true_total = scalar(db, "SELECT SUM(labor_hours) FROM work_orders")
    missing = scalar(db, "SELECT COUNT(*) FROM work_orders w WHERE NOT EXISTS "
                         "(SELECT 1 FROM parts_used pu WHERE pu.wo_id = w.wo_id)")
    assert report_number(text, "reported_total_labor_hours") == pytest.approx(reported, abs=0.06)
    assert report_number(text, "true_total_labor_hours") == pytest.approx(true_total, abs=0.06)
    assert report_number(text, "work_orders_missing_from_broken_query") == missing


def test_bug_report_sections_are_written(target):
    text = (target / "FANOUT_REPORT.md").read_text()
    sections = re.split(r"^## .*$", text, flags=re.M)[1:]
    assert len(sections) >= 4, "keep the four report sections"
    for i, body in enumerate(sections[:4], start=1):
        words = [w for w in body.split() if w != "TODO"]
        assert len(words) >= 12, f"section {i} of FANOUT_REPORT.md is still empty or a stub"
