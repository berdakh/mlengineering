"""Tests for the build tools and the mlcourse helpers. Fast; no data or network needed."""
from __future__ import annotations

import json
from pathlib import Path

import nbbuild
from mathmarkup import single_dollar_maths, to_double_dollar
from nbpages import unprotected_liquid

ROOT = Path(__file__).resolve().parents[1]


def test_percent_format_round_trip():
    src = "# %% [markdown]\n# # Title\n#\n# text\n\n# %%\nprint(1)\n"
    cells = nbbuild.parse_percent(src)
    assert [c["cell_type"] for c in cells] == ["markdown", "code"]
    assert "".join(cells[0]["source"]) == "# Title\n\ntext"
    assert "".join(cells[1]["source"]) == "print(1)"


def test_inline_maths_becomes_double_dollar_outside_code():
    md = "a $x_1$ b `$y$` c $$z$$\n```\n$w$\n```\n"
    out = to_double_dollar(md)
    assert "$$x_1$$" in out and "`$y$`" in out and "\n$w$\n" in out
    assert single_dollar_maths(out) == []


def test_every_notebook_has_one_source_and_course_entry():
    units = json.loads((ROOT / "advanced" / "course.json").read_text())["units"]
    names = sorted(u["notebook"] for u in units if u["notebook"])
    assert len(names) == 48
    assert sorted(p.stem for p in (ROOT / "advanced" / "notebook_src").glob("*.py")) == names
    assert sorted(p.stem for p in (ROOT / "advanced" / "notebooks").glob("*.ipynb")) == names


def test_site_pages_have_front_matter_and_no_unprotected_liquid():
    for page in (ROOT / "docs").rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{page} has no front matter"
        assert not unprotected_liquid(text), f"{page} has Liquid syntax outside a raw block"


def test_handbook_uses_double_dollar_maths():
    offenders = [str(p) for p in (ROOT / "docs" / "handbook").rglob("*.md") if single_dollar_maths(p.read_text())]
    assert not offenders


def test_mlcourse_finds_sessions_and_check_dirs():
    from mlcourse.checks import check_dirs
    from mlcourse.paths import find_unit, repo_root

    assert repo_root(ROOT / "labs") == ROOT
    assert find_unit("w3d4")["notebook"] == "16_point_vs_event_evaluation"
    assert find_unit("16")["id"] == "w3d4_point_vs_event_evaluation"
    assert [d.name for d in check_dirs("w3d4", root=ROOT)] == ["checks"]
    assert [d.name for d in check_dirs("w3d4", challenge=True, root=ROOT)] == ["checks_challenge"]
    sections = [d.parent.name for d in check_dirs("diagnostic", root=ROOT)]
    assert "a1_python" in sections and "b3_testing_api" in sections


def test_mark_writes_the_same_format_as_wb(tmp_path, monkeypatch):
    import mlcourse.progress as progress

    target = tmp_path / "progress.json"
    monkeypatch.setattr(progress, "_path", lambda: target)
    progress.mark("w1d3", "guided")
    data = json.loads(target.read_text())
    assert data["units"]["w1d3_package_structure"]["guided"] is True
