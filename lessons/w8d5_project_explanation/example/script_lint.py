"""Lint a spoken walkthrough script: speaking time per section, missing structure, bare numbers.

    python lessons/w8d5_project_explanation/example/script_lint.py <script.md> [--wpm 140]

A section is a `## ` heading. Speaking time assumes 140 words per minute (a calm interview pace;
measure your own with a recording and pass --wpm). It flags:
  * missing structural sections (Problem, Constraint, Decision, Evidence, Limitation, Next step);
  * numbers in the Evidence section with no interval or uncertainty statement next to them;
  * sections longer than 90 seconds in a 5-minute script;
  * jargon a non-specialist will not follow (a short, editable list).
It does not judge content. It only makes structure visible.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STRUCTURE = ["Problem", "Constraint", "Decision", "Evidence", "Limitation", "Next step"]
JARGON = ["AUC", "PR-AUC", "bootstrap", "nested", "Mahalanobis", "embargo", "non-inferiority", "p-value"]
NUMBER = re.compile(r"(?<![\w\[.])\d+(?:\.\d+)?\s*%?")
UNCERTAIN = re.compile(r"\[\s*[-+]?\d*\.?\d+\s*,\s*[-+]?\d*\.?\d+\s*\]|±|interval|between .* and", re.I)


def words(text: str) -> int:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return len([t for t in text.split() if re.search(r"[A-Za-z0-9]", t)])


def sections(text: str) -> dict[str, str]:
    out, current = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def lint(text: str, wpm: float = 140.0) -> tuple[list[tuple[str, int, float]], list[str]]:
    secs = sections(text)
    rows, warnings = [], []
    for heading, body in secs.items():
        n = words(body)
        rows.append((heading, n, 60.0 * n / wpm))
        if 60.0 * n / wpm > 90:
            warnings.append(f"'{heading}' takes {60.0 * n / wpm:.0f} s; over 90 s, the listener loses the thread")
        for term in JARGON:
            if re.search(rf"\b{re.escape(term)}\b", body):
                warnings.append(f"'{heading}' uses '{term}': explain it or replace it for a non-specialist")
    for name in STRUCTURE:
        if not any(h.lower().startswith(name.lower()) for h in secs):
            warnings.append(f"missing section '{name}'")
    evidence = next((b for h, b in secs.items() if h.lower().startswith("evidence")), "")
    for sentence in re.split(r"(?<=[.;])\s+", evidence):
        if NUMBER.search(sentence) and not UNCERTAIN.search(sentence):
            warnings.append(f"Evidence: number without uncertainty -> \"{sentence.strip()[:70]}...\"")
    return rows, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script")
    ap.add_argument("--wpm", type=float, default=140.0)
    args = ap.parse_args()
    rows, warnings = lint(Path(args.script).read_text(), args.wpm)
    print(f"{'section':<16}{'words':>7}{'seconds':>9}")
    for heading, n, sec in rows:
        print(f"{heading[:16]:<16}{n:>7}{sec:>9.0f}")
    total_w = sum(r[1] for r in rows)
    print(f"{'total':<16}{total_w:>7}{sum(r[2] for r in rows):>9.0f}")
    print()
    for w in warnings:
        print("WARN", w)
    print(f"{len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
