#!/usr/bin/env python3
"""Build .ipynb notebooks from jupytext-style "percent" .py sources.

Why this exists
---------------
Notebook JSON is painful to review in a pull request: one changed word shows up
as a rewritten blob. So the *source of truth* for every course notebook is a
plain Python file in ``notebook_src/`` using the percent format, and this script
renders the ``notebooks/*.ipynb`` that students actually open.

Percent format recap::

    # %% [markdown]
    # # A heading
    # Some prose.

    # %%
    print("a code cell")

Usage::

    python tools/nbbuild.py            # build every source
    python tools/nbbuild.py --check    # fail if notebooks are stale (CI)
    python tools/nbbuild.py 03_first_generation
    python tools/nbbuild.py --src advanced/notebook_src --out advanced/notebooks --solutions ""

Solutions (nbgrader-style). A code cell may contain one or more solution blocks::

    def total(xs):
        ### BEGIN SOLUTION
        return sum(xs)
        ### STARTER (optional: what the student sees instead; default is a TODO line)
        return None
        ### END SOLUTION

The student notebook gets the STARTER lines (or `# YOUR CODE HERE` + `raise NotImplementedError()`),
indented like the block; the solved notebook (``--solutions`` folder) gets the solution lines. Markdown
between ``<!-- BEGIN SOLUTION -->`` and ``<!-- END SOLUTION -->`` is likewise removed for students.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "notebook_src"
OUT_DIR = REPO_ROOT / "notebooks"
SOL_DIR = REPO_ROOT / "solutions" / "notebooks"
BEGIN, STARTER, END = "### BEGIN SOLUTION", "### STARTER", "### END SOLUTION"
MD_BEGIN, MD_END = "<!-- BEGIN SOLUTION -->", "<!-- END SOLUTION -->"


def strip_solutions(text: str, student: bool) -> str:
    """Resolve solution blocks in one cell body for the student or the solved version."""
    out: list[str] = []
    mode = None  # None | "solution" | "starter"
    indent = ""
    starter: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == BEGIN:
            mode, indent, starter = "solution", line[: len(line) - len(line.lstrip())], []
            continue
        if stripped == STARTER and mode == "solution":
            mode = "starter"
            continue
        if stripped == END and mode:
            if student:
                out.extend(starter or [indent + "# YOUR CODE HERE", indent + "raise NotImplementedError()"])
            mode = None
            continue
        if stripped == MD_BEGIN:
            mode = "md"
            continue
        if stripped == MD_END and mode == "md":
            mode = None
            continue
        if mode == "solution" or mode == "md":
            if not student:
                out.append(line)
        elif mode == "starter":
            starter.append(line)
        else:
            out.append(line)
    if mode:
        raise ValueError("unterminated solution block")
    return "\n".join(out)

KERNELSPEC = {
    "display_name": "Python 3 (ml-engineering)",
    "language": "python",
    "name": "python3",
}
LANGUAGE_INFO = {
    "codemirror_mode": {"name": "ipython", "version": 3},
    "file_extension": ".py",
    "mimetype": "text/x-python",
    "name": "python",
    "nbconvert_exporter": "python",
    "pygments_lexer": "ipython3",
}


def _as_source_lines(text: str) -> list[str]:
    """Split a cell body into nbformat's list-of-lines-with-newlines shape."""
    text = text.rstrip("\n")
    if not text:
        return []
    lines = text.split("\n")
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


def _strip_markdown_comments(body: str) -> str:
    """Turn ``# some text`` comment lines back into raw markdown."""
    out = []
    for line in body.split("\n"):
        if line.startswith("# "):
            out.append(line[2:])
        elif line.strip() == "#":
            out.append("")
        else:
            # A markdown cell should be fully commented; keep anything odd
            # verbatim rather than silently dropping content.
            out.append(line)
    return "\n".join(out)


def parse_percent(text: str) -> list[dict]:
    """Parse percent-format text into a list of nbformat cell dicts."""
    cells: list[dict] = []
    current_kind: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current_kind is None:
            return
        body = "\n".join(buffer).strip("\n")
        if not body.strip():
            return
        if current_kind == "markdown":
            cells.append(
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": _as_source_lines(_strip_markdown_comments(body)),
                }
            )
        else:
            cells.append(
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": _as_source_lines(body),
                }
            )

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# %%"):
            flush()
            buffer = []
            current_kind = "markdown" if "[markdown]" in stripped else "code"
            continue
        if current_kind is None:
            # Anything before the first cell marker (module docstring, etc.)
            continue
        buffer.append(line)

    flush()
    return cells


def build_notebook(src: Path, student: bool = True) -> dict:
    cells = parse_percent(src.read_text(encoding="utf-8"))
    for cell in cells:
        body = "".join(cell["source"])
        if "SOLUTION" in body:
            cell["source"] = _as_source_lines(strip_solutions(body, student))
    if not cells:
        raise ValueError(f"{src.name} produced no cells - is it percent-formatted?")
    return {
        "cells": cells,
        "metadata": {"kernelspec": KERNELSPEC, "language_info": LANGUAGE_INFO},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def render(nb: dict) -> str:
    return json.dumps(nb, indent=1, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("only", nargs="*", help="build only sources matching these substrings")
    parser.add_argument("--check", action="store_true", help="verify notebooks are up to date")
    parser.add_argument("--src", default=str(SRC_DIR.relative_to(REPO_ROOT)))
    parser.add_argument("--out", default=str(OUT_DIR.relative_to(REPO_ROOT)))
    parser.add_argument("--solutions", default=str(SOL_DIR.relative_to(REPO_ROOT)),
                        help='folder for solved notebooks ("" to skip)')
    args = parser.parse_args()
    src_dir, out_dir = REPO_ROOT / args.src, REPO_ROOT / args.out
    sol_dir = REPO_ROOT / args.solutions if args.solutions else None

    sources = sorted(src_dir.glob("*.py"))
    if args.only:
        sources = [s for s in sources if any(token in s.name for token in args.only)]
    if not sources:
        print("no notebook sources matched", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    if sol_dir:
        sol_dir.mkdir(parents=True, exist_ok=True)
    stale: list[str] = []
    for src in sources:
        targets = [(out_dir / (src.stem + ".ipynb"), True)]
        if sol_dir and "SOLUTION" in src.read_text(encoding="utf-8"):
            targets.append((sol_dir / (src.stem + ".ipynb"), False))
        for out, student in targets:
            text = render(build_notebook(src, student))
            if args.check:
                if not out.exists() or out.read_text(encoding="utf-8") != text:
                    stale.append(str(out.relative_to(REPO_ROOT)))
                continue
            out.write_text(text, encoding="utf-8")
            n_cells = len(json.loads(text)["cells"])
            print(f"built {out.relative_to(REPO_ROOT)}  ({n_cells} cells)")

    if args.check:
        if stale:
            print("stale notebooks (run `python tools/nbbuild.py`):", file=sys.stderr)
            for name in stale:
                print(f"  - {name}", file=sys.stderr)
            return 1
        print(f"all {len(sources)} notebooks up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
