"""lab/DELIVERABLES.md must account for every deliverable in docs/guides/project.md."""
from __future__ import annotations

import re

import pytest

from conftest import ROOT

STATUSES = {"done", "partial", "scoped out"}


def project_deliverables() -> list[str]:
    text = (ROOT / "docs" / "guides" / "project.md").read_text()
    section = text.split("## Deliverables checklist", 1)[1].split("\n## ", 1)[0]
    rows = [r for r in section.splitlines() if r.startswith("|")][2:]
    return [r.split("|")[1].strip() for r in rows]


@pytest.fixture(scope="session")
def table(target) -> dict[str, tuple[str, str]]:
    path = target / "DELIVERABLES.md"
    assert path.is_file(), "missing lab/DELIVERABLES.md"
    out = {}
    for row in path.read_text().splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] and not set(cells[0]) <= set("-: ") and cells[0] != "Deliverable":
            out[cells[0].lower()] = (cells[1].lower(), cells[2])
    return out


def test_every_project_deliverable_listed(table):
    missing = [d for d in project_deliverables() if d.lower() not in table]
    assert not missing, f"DELIVERABLES.md lacks rows for: {missing}"


def test_status_values(table):
    bad = {k: v[0] for k, v in table.items() if v[0] not in STATUSES}
    assert not bad, f"status must be one of {sorted(STATUSES)}: {bad}"


def test_done_items_have_evidence(table):
    weak = [k for k, (status, ev) in table.items()
            if status == "done" and not re.search(r"`[^`]+`|https?://", ev)]
    assert not weak, f"'done' needs evidence a reviewer can open (a `path` or a URL): {weak}"


def test_partial_and_scoped_out_items_have_reasons(table):
    weak = [k for k, (status, ev) in table.items() if status != "done" and len(ev.split()) < 8]
    assert not weak, f"say why (8+ words) for partial or scoped-out items: {weak}"
