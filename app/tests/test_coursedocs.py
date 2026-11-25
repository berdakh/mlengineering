"""Tests for the study app's pure helpers. Run: python -m pytest app/tests -q"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coursedocs as cd  # noqa: E402


def test_split_blocks_separates_mermaid_and_images(tmp_path):
    md = "# T\n\ntext\n\n```mermaid\nflowchart LR\n  a --> b\n```\n\n![fig](figures/x.svg)\n\nafter\n"
    blocks = cd.split_blocks(md, tmp_path)
    kinds = [b.kind for b in blocks]
    assert kinds == ["markdown", "mermaid", "image", "markdown"]  # whitespace-only text is dropped
    assert blocks[1].text == "flowchart LR\n  a --> b"
    assert blocks[2].text == str((tmp_path / "figures/x.svg").resolve()) and blocks[2].alt == "fig"


def test_split_blocks_keeps_remote_images_inline(tmp_path):
    md = "![badge](https://example.org/b.svg)\n"
    assert [b.kind for b in cd.split_blocks(md, tmp_path)] == ["markdown"]


def test_rewrite_links_routes_markdown_and_readme_dirs(tmp_path):
    (tmp_path / "lessons/a").mkdir(parents=True)
    (tmp_path / "lessons/a/README.md").write_text("x")
    (tmp_path / "lessons/b.md").write_text("y")
    (tmp_path / "lessons/data.csv").write_text("z")
    doc = tmp_path / "lessons/index.md"
    out = cd.rewrite_links("[A](a/) [B](b.md#sec) [D](data.csv) [W](https://x.org) ![i](f.svg)", doc, tmp_path)
    assert "[A](?doc=lessons/a/README.md)" in out
    assert "[B](?doc=lessons/b.md)" in out
    assert "D (`lessons/data.csv`)" in out
    assert "[W](https://x.org)" in out and "![i](f.svg)" in out


def test_safe_doc_refuses_outside_paths_and_non_markdown(tmp_path):
    (tmp_path / "ok.md").write_text("x")
    (tmp_path / "secret.txt").write_text("x")
    assert cd.safe_doc("ok.md", tmp_path) == (tmp_path / "ok.md").resolve()
    assert cd.safe_doc("../etc/passwd", tmp_path) is None
    assert cd.safe_doc("secret.txt", tmp_path) is None
    assert cd.safe_doc("missing.md", tmp_path) is None
    assert cd.safe_doc(None, tmp_path) is None


def test_set_flag_matches_wb_format(tmp_path):
    p = tmp_path / "progress.json"
    cd.set_flag("w1d3_package_structure", "guided", True, p)
    data = json.loads(p.read_text())
    assert data["units"]["w1d3_package_structure"]["guided"] is True
    cd.set_flag("w1d3_package_structure", "guided", False, p)
    assert json.loads(p.read_text())["units"]["w1d3_package_structure"]["guided"] is False


def test_next_unit_skips_done_and_planned():
    units = [{"id": "a", "path": "x", "status": "Execution verified"},
             {"id": "b", "path": None, "status": "Planned"},
             {"id": "c", "path": "y", "status": "Execution verified"}]
    assert cd.next_unit(units, {"units": {}})["id"] == "a"
    assert cd.next_unit(units, {"units": {"a": {"guided": True}}})["id"] == "c"
    assert cd.next_unit(units, {"units": {"a": {"independent": True}, "c": {"guided": True}}}) is None


def test_check_dirs_finds_nested_sections():
    dirs = [d.relative_to(cd.ROOT).as_posix() for d in cd.check_dirs("diagnostic")]
    assert "diagnostic/a1_python/checks" in dirs
    assert all("/checks" in d for d in dirs)


def test_every_unit_page_and_handbook_section_exists():
    for unit in cd.load_units():
        assert (cd.ROOT / unit["path"] / "README.md").is_file(), unit["id"]
    assert len(cd.handbook_sections()) == 55
