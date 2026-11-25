"""Fixtures for the w6d6 challenge checks: grades <target>/POSTMORTEM.md against the given timeline."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w6d6_cd_ops_debugging"


@pytest.fixture(scope="session")
def text() -> str:
    path = resolve_target(UNIT, "challenge") / "POSTMORTEM.md"
    assert path.is_file(), f"missing {path}"
    return re.sub(r"<!--.*?-->", "", path.read_text(), flags=re.S)


@pytest.fixture(scope="session")
def given_times() -> set[str]:
    timeline = (ROOT / UNIT / "challenge" / "given" / "INCIDENT_TIMELINE.md").read_text()
    return set(re.findall(r"^\| (\d\d:\d\d) \|", timeline, flags=re.M))


def sections(text: str) -> dict[str, str]:
    out, current = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def section(text: str, name: str) -> str:
    secs = sections(text)
    key = next((k for k in secs if k.startswith(name.lower())), None)
    assert key is not None, f"POSTMORTEM.md needs a '## {name}' section"
    return secs[key]
