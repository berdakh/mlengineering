"""w8d5 challenge checks: structure of the research walkthrough and the adversarial answers."""
import re

import pytest

from w8d5_text import INTERVAL, PLACEHOLDERS, UNIT, find_section, resolve_target, sections, words

TARGET = resolve_target(UNIT, "challenge")
STRUCTURE = ["Problem", "Constraint", "Decision", "Evidence", "Limitation", "Next step"]


def read(name):
    path = TARGET / name
    assert path.is_file(), f"missing {path}"
    return path.read_text()


def test_no_placeholders_left():
    for name in ("RESEARCH_WALKTHROUGH.md", "ADVERSARIAL.md"):
        assert not PLACEHOLDERS.search(read(name)), f"{name} still contains a placeholder"


def test_research_walkthrough_structure():
    secs = sections(read("RESEARCH_WALKTHROUGH.md"))
    for name in STRUCTURE:
        body = find_section(secs, name)
        assert body is not None, f"missing section '## {name}'"
        assert words(body) >= 40, f"section '{name}' has {words(body)} words; at least 40"
    total = sum(words(find_section(secs, n) or "") for n in STRUCTURE)
    assert 550 <= total <= 800, f"the six spoken sections have {total} words; 550-800 for 5 minutes"


def test_translation_and_not_established_sections():
    secs = sections(read("RESEARCH_WALKTHROUGH.md"))
    translation = find_section(secs, "Translation to industry")
    assert translation is not None and words(translation) >= 60, "'## Translation to industry', at least 60 words"
    not_established = find_section(secs, "What was not established")
    assert not_established is not None and words(not_established) >= 40, \
        "'## What was not established', at least 40 words"


def test_evidence_states_uncertainty():
    evidence = find_section(sections(read("RESEARCH_WALKTHROUGH.md")), "Evidence") or ""
    assert INTERVAL.search(evidence) or re.search(r"no interval", evidence, re.I), (
        "quote a result with its interval, or say explicitly that no interval is available and why")


@pytest.fixture(scope="module")
def adversarial():
    return {h: b for h, b in sections(read("ADVERSARIAL.md")).items() if re.fullmatch(r"A\d", h)}


def test_five_adversarial_answers(adversarial):
    assert sorted(adversarial) == [f"A{i}" for i in range(1, 6)], f"expected ## A1 ... ## A5, got {sorted(adversarial)}"


@pytest.mark.parametrize("a", [f"A{i}" for i in range(1, 6)])
def test_adversarial_answer_shape(adversarial, a):
    body = adversarial.get(a, "")
    for move in ("Question:", "Concede:", "Quantify:", "Redirect:"):
        assert re.search(rf"^\s*\**{move}", body, flags=re.M), f"{a}: add a line starting '{move}'"
    answer = "\n".join(line for line in body.splitlines() if not re.match(r"^\s*\**Question:", line))
    assert words(answer) <= 120, f"{a}: {words(answer)} words; keep a spoken answer under 120"
