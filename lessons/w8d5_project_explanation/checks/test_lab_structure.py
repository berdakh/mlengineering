"""w8d5 lab checks: STRUCTURE only. They cannot judge whether an answer is good - the rubric in
../assessment.md and a recorded run do that. They do catch missing answers, answers too long to say
in an interview, claims with no artifact behind them, and scripts missing the limitation."""
import re

import pytest

from w8d5_text import (INTERVAL, PLACEHOLDERS, UNIT, artifact_exists, find_section, resolve_target,
                       sections, words)

TARGET = resolve_target(UNIT)


def read(name):
    path = TARGET / name
    assert path.is_file(), f"missing {path}"
    return path.read_text()


# ------------------------------------------------------------------ ANSWERS.md
@pytest.fixture(scope="module")
def answers():
    secs = sections(read("ANSWERS.md"))
    return {h: b for h, b in secs.items() if re.fullmatch(r"Q\d\d", h)}


def test_all_twenty_questions_answered(answers):
    missing = [f"Q{i:02d}" for i in range(1, 21) if f"Q{i:02d}" not in answers]
    assert not missing, f"no answer for {missing}"


@pytest.mark.parametrize("q", [f"Q{i:02d}" for i in range(1, 21)])
def test_answer_length_and_evidence(answers, q):
    body = answers.get(q, "")
    assert not PLACEHOLDERS.search(body), f"{q} still contains a placeholder"
    evidence = [line for line in body.splitlines() if line.strip().lower().startswith("evidence:")]
    assert evidence, f"{q}: add a line starting 'Evidence:' that names an artifact"
    text = "\n".join(line for line in body.splitlines() if not line.strip().lower().startswith("evidence:"))
    n = words(text)
    assert 40 <= n <= 130, f"{q}: {n} words; spoken answers of 40-130 words (about 20-50 s) work in interviews"
    paths = re.findall(r"`([^`]+)`", " ".join(evidence))
    assert paths, f"{q}: put the artifact path in backticks"
    dead = [p for p in paths if not artifact_exists(p.strip())]
    assert not dead, f"{q}: cited artifact(s) not found: {dead}"


# ------------------------------------------------------------------ walkthroughs
def test_thirty_second_version():
    text = re.sub(r"^#.*$", "", read("WALKTHROUGH_30S.md"), flags=re.M)
    assert not PLACEHOLDERS.search(text)
    assert 40 <= words(text) <= 90, f"{words(text)} words; 30 seconds is 40-90 words"


STRUCTURE = ["Problem", "Constraint", "Decision", "Evidence", "Limitation", "Next step"]


def test_five_minute_script_structure_and_length():
    text = read("WALKTHROUGH_5MIN.md")
    assert not PLACEHOLDERS.search(text), "the script still contains a placeholder"
    secs = sections(text)
    for name in STRUCTURE:
        body = find_section(secs, name)
        assert body is not None, f"missing section '## {name}'"
        assert words(body) >= 40, f"section '{name}' has {words(body)} words; at least 40"
    total = sum(words(b) for b in secs.values())
    assert 550 <= total <= 800, f"{total} words: 5 minutes at about 140 words per minute is 550-800"


def test_five_minute_evidence_has_an_interval():
    evidence = find_section(sections(read("WALKTHROUGH_5MIN.md")), "Evidence") or ""
    assert INTERVAL.search(evidence), "give at least one number with its interval, e.g. 0.88 [0.81, 0.93]"


def test_twenty_minute_outline():
    text = read("OUTLINE_20MIN.md")
    assert not PLACEHOLDERS.search(text)
    minutes = [float(m) for m in re.findall(r"^\s*[-*]\s*\[\s*(\d+(?:\.\d+)?)\s*min\s*\]", text, flags=re.M)]
    assert len(minutes) >= 6, f"{len(minutes)} timed parts; at least 6"
    assert 18 <= sum(minutes) <= 22, f"parts add up to {sum(minutes)} min; aim for 18-22"


def test_slide_outline():
    text = read("SLIDES.md")
    assert not PLACEHOLDERS.search(text), "the slide outline still contains a placeholder"
    slides = sections(text)
    assert 5 <= len(slides) <= 12, f"{len(slides)} slides; 5-12"
    assert "```mermaid" in text, "one architecture diagram as a mermaid block"
    table_rows = [line for line in text.splitlines() if line.strip().startswith("|")]
    assert any(INTERVAL.search(r) for r in table_rows), "a results table with intervals"
    assert any("failure example" in h.lower() for h in slides), "one slide titled '... Failure example ...'"
