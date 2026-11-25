#!/usr/bin/env python3
"""Workbench helper: see where you are, run checks, record progress.

    python wb.py status                       # roadmap position and progress flags
    python wb.py next                         # the next unit that is ready to study
    python wb.py check <unit> [--challenge]   # run a unit's checks against YOUR work
    python wb.py mark <unit> <flag> [off]     # flag: reading | guided | independent | review
    python wb.py note <unit> "text"           # append a dated note to progress/notes.md

<unit> is an id or path, e.g.  w1d3  or  labs/w1d3_package_structure  or  diagnostic/a1_python

Progress lives in progress/progress.json (plain JSON, yours to edit and commit).
The four flags are deliberately separate: passing supplied checks sets nothing by
itself, and 'independent' should only be set after unassisted work.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COURSE = ROOT / "course.json"
PROGRESS = ROOT / "progress" / "progress.json"
FLAGS = ("reading", "guided", "independent", "review")


def load_units() -> list[dict]:
    return json.loads(COURSE.read_text())["units"]


def load_progress() -> dict:
    return json.loads(PROGRESS.read_text()) if PROGRESS.is_file() else {"units": {}}


def save_progress(progress: dict) -> None:
    PROGRESS.parent.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n")


def find_unit(token: str) -> dict:
    token = token.strip("/")
    matches = [u for u in load_units()
               if token in (u["id"], u.get("path")) or u["id"].startswith(token + "_")
               or (u.get("path") or "").endswith("/" + token)]
    if len(matches) != 1:
        sys.exit(f"unit '{token}' matched {len(matches)} units; use an id from `python wb.py status`")
    return matches[0]


def cmd_status(_: argparse.Namespace) -> None:
    progress = load_progress()["units"]
    print(f"{'unit':<28}{'content status':<21}{'read':<6}{'guided':<8}{'indep':<7}{'review':<7} title")
    week = None
    for u in load_units():
        if u["week"] != week:
            week = u["week"]
            print(f"--- Week {week} ---")
        p = progress.get(u["id"], {})
        cell = lambda f: "x" if p.get(f) else "."  # noqa: E731
        print(f"{u['id']:<28}{u['status']:<21}{cell('reading'):<6}{cell('guided'):<8}"
              f"{cell('independent'):<7}{cell('review'):<7} {u['title']}")
    print("\nFlags: read = reading completed, guided = guided practice completed,\n"
          "indep = independent skill demonstrated, review = review needed.")


def cmd_next(_: argparse.Namespace) -> None:
    progress = load_progress()["units"]
    for u in load_units():
        p = progress.get(u["id"], {})
        if u["status"] != "Planned" and not (p.get("guided") or p.get("independent")):
            print(f"Next: {u['id']} - {u['title']}\nOpen: {u['path']}/README.md")
            return
    print("All authored units are marked done. See docs/guides/status.md.")


def cmd_check(args: argparse.Namespace) -> None:
    token = args.unit.strip("/")
    if (ROOT / token).is_dir():          # a path such as diagnostic/a1_python
        path, label = token, token
    else:
        unit = find_unit(token)
        if not unit.get("path"):
            sys.exit(f"{unit['id']} is planned; it has no material yet")
        path, label = unit["path"], unit["id"]
    checks = ROOT / path / ("checks_challenge" if args.challenge else "checks")
    if not checks.is_dir():
        sys.exit(f"{label} has no {checks.name}/ directory (nothing to check automatically)")
    code = subprocess.call([sys.executable, "-m", "pytest", str(checks), "-q"], cwd=ROOT)
    if code == 0:
        print("\nChecks pass. That is 'guided practice completed' at most. Record progress yourself\n"
              "with `python wb.py mark <unit> guided` (see `python wb.py status` for unit ids).")
    sys.exit(code)


def cmd_mark(args: argparse.Namespace) -> None:
    unit = find_unit(args.unit)
    progress = load_progress()
    entry = progress["units"].setdefault(unit["id"], {})
    entry[args.flag] = args.state != "off"
    entry["updated"] = dt.date.today().isoformat()
    save_progress(progress)
    print(f"{unit['id']}: {args.flag} = {entry[args.flag]}")


def cmd_note(args: argparse.Namespace) -> None:
    unit = find_unit(args.unit)
    notes = ROOT / "progress" / "notes.md"
    with notes.open("a") as fh:
        fh.write(f"\n## {dt.date.today().isoformat()} - {unit['id']}\n\n{args.text}\n")
    print(f"appended to {notes.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("next").set_defaults(fn=cmd_next)
    c = sub.add_parser("check"); c.add_argument("unit"); c.add_argument("--challenge", action="store_true")
    c.set_defaults(fn=cmd_check)
    m = sub.add_parser("mark"); m.add_argument("unit"); m.add_argument("flag", choices=FLAGS)
    m.add_argument("state", nargs="?", default="on", choices=["on", "off"]); m.set_defaults(fn=cmd_mark)
    n = sub.add_parser("note"); n.add_argument("unit"); n.add_argument("text"); n.set_defaults(fn=cmd_note)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
