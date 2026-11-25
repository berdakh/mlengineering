"""Check a technical report against the results it claims to report (reference solution, w8d2).

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
    """Remove the parts of a line whose numbers are not results: code spans, link targets, dates, versions."""
    line = re.sub(r"`[^`]*`", " ", line)
    line = re.sub(r"\]\([^)]*\)", "] ", line)
    line = re.sub(r"https?://\S+", " ", line)
    line = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", line)
    line = re.sub(r"\b\d+(\.\d+){2,}\b", " ", line)
    line = re.sub(r"^\s*(\d+\.|[-*])\s+", " ", line)  # list markers
    return line


def traced(token: str, percent: bool, leaves: list[float]) -> bool:
    value = float(token.replace(",", ""))
    decimals = len(token.split(".")[1]) if "." in token else 0
    for v in leaves:
        candidate = v
        if round(candidate, decimals) == round(value, decimals):
            return True
    return False


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
    lines = report.splitlines()
    found: list[dict] = []
    secs = sections(lines)
    for req in REQUIRED_SECTIONS:
        if not any(title.lower().startswith(req.lower()) for title in secs):
            found.append(finding("missing_section", 0, f"no '## {req}...' section"))

    leaves = numeric_leaves(results)
    in_code = False
    for i, raw in enumerate(lines, 1):
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or raw.lstrip().startswith("#") or raw.lstrip().startswith("!["):
            continue
        for m in NUMBER.finditer(strip_markup(raw)):
            token, percent = m.group(1), bool(m.group(2))
            if not traced(token, percent, leaves):
                found.append(finding("untraced_number", i,
                                     f"{token}{'%' if percent else ''} does not appear in the results file "
                                     "(at the precision written)"))

    for start, block in blocks(lines):
        text = " ".join(block)
        if INTERVAL.search(text) and not METHOD.search(text):
            found.append(finding("interval_without_unit", start,
                                 "an interval without saying how it was obtained (bootstrap over what? Wilson?)"))
        if SIGNIFICANT.search(text) and not TEST_REF.search(text):
            found.append(finding("significance_without_test", start,
                                 "'significant' without naming the test or giving a p value"))

    lim = next(((a, b) for t, (a, b) in secs.items() if t.lower().startswith("limitations")), None)
    if lim:
        items, cur = [], None
        for line in lines[lim[0] + 1:lim[1]]:
            if re.match(r"^\s*([-*]|\d+\.)\s+", line):
                cur = [line]
                items.append(cur)
            elif cur is not None and line.startswith("  ") and line.strip():
                cur.append(line)
            elif not line.strip():
                cur = None
        complete = [it for it in items
                    if re.search(r"impact\s*:", " ".join(it), re.I) and re.search(r"mitigation\s*:", " ".join(it), re.I)]
        if len(items) < min_limitations or len(complete) < len(items):
            found.append(finding("limitations_incomplete", lim[0] + 1,
                                 f"{len(items)} limitation item(s), {len(complete)} with both 'Impact:' and "
                                 f"'Mitigation:'; need at least {min_limitations}, all complete"))
    return found


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
