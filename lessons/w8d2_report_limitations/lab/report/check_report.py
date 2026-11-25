"""Check a technical report against the results it claims to report (w8d2 lab starter: implement strip_markup, traced and check).

    python report/check_report.py TECHNICAL_REPORT.md --results results.json [--min-limitations 5] [--json OUT]

Rules (each failure is a finding with a code; exit 0 if there are none, 1 otherwise, 2 on usage errors):

* ``missing_section``: every required ``## `` section is present (matched by its leading words,
  case-insensitive, ignoring a leading number such as ``## 3.``).
* ``untraced_number``: every number in the body text and tables appears in the results JSON. A number
  written with d decimals matches a numeric leaf v when round(v, d) equals it; a number followed by ``%``
  matches round(100 v, d). Thousands separators (``46,806``) are allowed. Not checked: headings, inline
  code and code blocks, link targets, dates (2026-11-22), version strings (3.13.18) and numbers that are
  part of an identifier (``valve1/8``, ``w4d6``, ``H15.6``, ``v2``).
* ``interval_without_unit``: every Markdown block (paragraph, list item group or table with its caption
  line) that contains an interval ``[a, b]`` also says how it was obtained (``bootstrap``, ``resampl...``,
  ``Wilson`` or ``unit of analysis``).
* ``significance_without_test``: a block that says "significant(ly)" also names the test or gives a p
  value (``test``, ``p =``, ``p-value``).
* ``limitations_incomplete``: the Limitations section has at least ``--min-limitations`` list items and each
  item states an ``Impact:`` and a ``Mitigation:``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = ("Problem", "Data", "Protocol", "Results", "Error analysis", "Decision",
                     "Serving and monitoring", "Limitations", "Reproducibility")

NUMBER = re.compile(r"(?<![\w./\-−])(-?\d{1,3}(?:,\d{3})+|-?\d+(?:\.\d+)?)(?![\w/\-]|\.\d|,\d{3})(\s?%)?")
INTERVAL = re.compile(r"\[\s*-?\d[\d.,]*\s*,\s*-?\d[\d.,]*\s*\]")
METHOD = re.compile(r"bootstrap|resampl|wilson|unit of analysis", re.I)
SIGNIFICANT = re.compile(r"\bsignifican(t|tly|ce)\b", re.I)
TEST_REF = re.compile(r"\btest\b|\bp\s*=|p-value", re.I)


def finding(code: str, line: int, detail: str) -> dict:
    return {"code": code, "line": line, "detail": detail}


def numeric_leaves(obj) -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out += numeric_leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            out += numeric_leaves(v)
    return out


def strip_markup(line: str) -> str:
    """Blank out the parts of a line whose numbers are not results: inline code, link targets, URLs,
    dates (YYYY-MM-DD), version strings (a.b.c) and list markers. Return the cleaned line.
    """
    raise NotImplementedError("strip_markup: write me (see the lab README)")


def traced(token: str, percent: bool, leaves: list[float]) -> bool:
    """True if `token` (e.g. '0.884', '46,806', '-0.06') matches some numeric leaf at the precision written:
    round(leaf, d) == round(value, d) with d = decimals in token; if `percent`, compare against 100 * leaf.
    """
    raise NotImplementedError("traced: write me (see the lab README)")


def blocks(lines: list[str]) -> list[tuple[int, list[str]]]:
    """Split into blocks separated by blank lines; returns (first line number, lines)."""
    out, cur, start, in_code = [], [], 0, False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line.strip():
            if cur:
                out.append((start, cur))
            cur = []
            continue
        if not cur:
            start = i
        cur.append(line)
    if cur:
        out.append((start, cur))
    return out


def sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    heads = [(i, re.sub(r"^##\s+(\d+\.?\s*)?", "", l).strip()) for i, l in enumerate(lines) if re.match(r"^##\s", l)]
    out = {}
    for k, (i, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        out[title] = (i, end)
    return out


def check(report: str, results: dict, min_limitations: int = 5) -> list[dict]:
    """Apply the five rules in the module docstring to `report`; return a list of finding(code, line, detail).
    Use sections(), blocks(), numeric_leaves(), strip_markup(), traced() and the regexes above.
    """
    raise NotImplementedError("check: write me (see the lab README)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a report against its results file.")
    ap.add_argument("report")
    ap.add_argument("--results", required=True)
    ap.add_argument("--min-limitations", type=int, default=5)
    ap.add_argument("--json", help="also write the findings as JSON to this file")
    args = ap.parse_args(argv)
    try:
        report = Path(args.report).read_text()
        results = json.loads(Path(args.results).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    found = check(report, results, args.min_limitations)
    verdict = "PASS" if not found else "FAIL"
    if args.json:
        Path(args.json).write_text(json.dumps({"verdict": verdict, "findings": found}, indent=2) + "\n")
    print(f"{verdict}: {len(found)} finding(s)")
    for f in found:
        print(f"  line {f['line']}: {f['code']}: {f['detail']}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
