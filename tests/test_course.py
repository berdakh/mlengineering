"""Consistency of the 12-week course: curriculum, notebooks, graders, guides, SQL helper."""
from __future__ import annotations

import importlib
import json
import re
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CURRICULUM = json.loads((ROOT / "curriculum.json").read_text())
NOTEBOOKS = [n["notebook"] for n in CURRICULUM["notebooks"]]
CALL = re.compile(r"""\b(grade|quiz)\(\s*["']([\w.]+)["']""")


def test_curriculum_shape():
    assert len(CURRICULUM["weeks"]) == 12
    assert len(NOTEBOOKS) == 48 == len(set(NOTEBOOKS))
    for week in range(1, 13):
        kinds = [n["kind"] for n in CURRICULUM["notebooks"] if n["week"] == week]
        assert kinds == ["lesson", "lesson", "lesson", "lab"], f"week {week}: {kinds}"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_every_notebook_exists_in_all_three_forms(name):
    assert (ROOT / "notebook_src" / f"{name}.py").is_file()
    assert (ROOT / "notebooks" / f"{name}.ipynb").is_file()
    assert (ROOT / "solutions" / "notebooks" / f"{name}.ipynb").is_file()


def test_tool_guides_and_week_pages_exist():
    for g in CURRICULUM["tool_guides"]:
        assert (ROOT / "docs" / "tools" / f"{g['guide']}.md").is_file(), g["guide"]
    for w in CURRICULUM["weeks"]:
        assert (ROOT / "docs" / "weeks" / f"week-{w['week']}.md").is_file(), w["week"]


def _keys_used(week: int) -> set[str]:
    used: set[str] = set()
    for n in CURRICULUM["notebooks"]:
        if n["week"] == week:
            used |= {k for _, k in CALL.findall((ROOT / "notebook_src" / f"{n['notebook']}.py").read_text())}
    return used


@pytest.mark.parametrize("week", range(1, 13))
def test_every_graded_cell_has_a_test_and_every_test_is_used(week):
    from mlcourse import grader

    mod = importlib.import_module(f"mlcourse.graders.w{week:02d}")
    prefix = f"w{week:02d}."
    registered = {k for k in [*grader._EXERCISES, *grader._QUIZZES] if k.startswith(prefix)}
    used = {k for k in _keys_used(week) if k.startswith(prefix)}
    assert mod is not None
    assert used - registered == set(), f"graded in notebooks but no test: {sorted(used - registered)}"
    assert registered - used == set(), f"tests no notebook uses: {sorted(registered - used)}"


def test_grader_outcomes(monkeypatch):
    from mlcourse import grader
    from mlcourse.grader import exercise, grade

    monkeypatch.setattr(grader, "_load", lambda key: None)  # no module behind the test prefix

    @exercise("t00.double", hint="multiply by two")
    def _check(fn):
        assert fn(2) == 4, "double(2) should be 4"

    def missing(x):
        raise NotImplementedError

    not_attempted = grade("t00.double", missing)
    assert not not_attempted and "not attempted" in repr(not_attempted)
    wrong = grade("t00.double", lambda x: x + 1)
    assert not wrong and "should be 4" in repr(wrong) and "multiply by two" in repr(wrong)
    assert grade("t00.double", lambda x: 2 * x)


def test_sql_helper_is_read_only():
    from mlcourse.sql import connect, sql

    assert int(sql("SELECT COUNT(*) AS n FROM customers")["n"][0]) > 0
    con = connect("shop")
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM customers")
