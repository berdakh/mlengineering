"""Pure helpers for the study app: course data, progress, Markdown splitting and link rewriting.

Kept free of Streamlit so it can be unit-tested (app/tests/) and reused by other tools.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / "course.json"
PROGRESS = ROOT / "progress" / "progress.json"
NOTES = ROOT / "progress" / "notes.md"
FLAGS = ("reading", "guided", "independent", "review")
FLAG_LABELS = {
    "reading": "Reading completed",
    "guided": "Guided practice completed",
    "independent": "Independent skill demonstrated",
    "review": "Review needed",
}


# --------------------------------------------------------------------------- course and progress
def load_units(course: Path = COURSE) -> list[dict]:
    return json.loads(course.read_text())["units"]


def load_progress(path: Path = PROGRESS) -> dict:
    return json.loads(path.read_text()) if path.is_file() else {"units": {}}


def set_flag(unit_id: str, flag: str, value: bool, path: Path = PROGRESS) -> dict:
    """Same file and format as `python wb.py mark`, so the CLI and the app never disagree."""
    if flag not in FLAGS:
        raise ValueError(f"unknown flag {flag!r}; expected one of {FLAGS}")
    progress = load_progress(path)
    entry = progress.setdefault("units", {}).setdefault(unit_id, {})
    entry[flag] = bool(value)
    entry["updated"] = dt.date.today().isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n")
    return progress


def append_note(unit_id: str, text: str, path: Path = NOTES) -> None:
    """Same format as `python wb.py note`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(f"\n## {dt.date.today().isoformat()} - {unit_id}\n\n{text.strip()}\n")


def next_unit(units: list[dict], progress: dict) -> dict | None:
    """First unit with material that is not yet marked guided or independent (as `wb.py next`)."""
    done = progress.get("units", {})
    for unit in units:
        p = done.get(unit["id"], {})
        if unit.get("path") and unit["status"] != "Planned" and not (p.get("guided") or p.get("independent")):
            return unit
    return None


def check_dirs(unit_path: str, root: Path = ROOT) -> list[Path]:
    """Every checks directory belonging to a unit, including nested sections
    (diagnostic/a1_python/checks, lessons/w8d6_final_assessment/f1_python/checks)."""
    base = root / unit_path
    found = [p for pattern in ("checks*", "*/checks*") for p in base.glob(pattern) if p.is_dir()]
    return sorted(found)


@dataclass
class CheckResult:
    passed: bool
    summary: str
    output: str


def run_checks(checks: Path, root: Path = ROOT, timeout: int = 600) -> CheckResult:
    """Run one checks directory against the learner's work, exactly as `wb.py check` does."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(checks), "-q", "-p", "no:cacheprovider"],
            cwd=root, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(False, f"timed out after {timeout} s", "")
    output = proc.stdout + proc.stderr
    lines = [ln for ln in output.strip().splitlines() if ln.strip()]
    summary = lines[-1].strip("= ") if lines else "no output"
    return CheckResult(proc.returncode == 0, summary, output)


# --------------------------------------------------------------------------- Markdown
@dataclass
class Block:
    kind: str  # "markdown" | "mermaid" | "image"
    text: str  # markdown text, mermaid source, or resolved image path
    alt: str = ""


FENCE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
IMAGE_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$", re.M)


def split_blocks(markdown: str, doc_dir: Path) -> list[Block]:
    """Split a document into Markdown, Mermaid and image blocks.

    Mermaid fences become their own blocks (rendered by the browser). A line that is only a local image
    becomes an image block with an absolute path; Streamlit's Markdown cannot resolve relative paths.
    """
    blocks: list[Block] = []
    pos = 0
    for m in FENCE.finditer(markdown):
        blocks.extend(_split_images(markdown[pos:m.start()], doc_dir))
        blocks.append(Block("mermaid", m.group(1).rstrip()))
        pos = m.end()
    blocks.extend(_split_images(markdown[pos:], doc_dir))
    return [b for b in blocks if b.kind != "markdown" or b.text.strip()]


def _split_images(text: str, doc_dir: Path) -> list[Block]:
    out: list[Block] = []
    pos = 0
    for m in IMAGE_LINE.finditer(text):
        target = m.group(2)
        if target.startswith(("http://", "https://")):
            continue
        out.append(Block("markdown", text[pos:m.start()]))
        out.append(Block("image", str((doc_dir / target).resolve()), alt=m.group(1)))
        pos = m.end()
    out.append(Block("markdown", text[pos:]))
    return out


LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s#]+)(#[^)\s]*)?\)")


def rewrite_links(markdown: str, doc_path: Path, root: Path = ROOT) -> str:
    """Point relative links at other course documents to the app (?doc=...), so clicking stays in the app.

    Links to Markdown files and to directories with a README open in the app; links to other local files
    are left as plain text with their repository path, because the browser cannot open them directly.
    """
    doc_dir = doc_path.parent

    def repl(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:")):
            return m.group(0)
        resolved = (doc_dir / target).resolve()
        try:
            rel = resolved.relative_to(root.resolve())
        except ValueError:
            return label
        if resolved.is_dir() and (resolved / "README.md").is_file():
            rel = rel / "README.md"
        if rel.suffix == ".md":
            return f"[{label}](?doc={rel.as_posix()})"
        return f"{label} (`{rel.as_posix()}`)"

    return LINK.sub(repl, markdown)


def safe_doc(path_param: str | None, root: Path = ROOT) -> Path | None:
    """Resolve a ?doc= parameter to a Markdown file inside the repository, or None.

    The app only ever displays .md files under the repository root; anything else is refused.
    """
    if not path_param:
        return None
    candidate = (root / path_param).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if candidate.suffix != ".md" or not candidate.is_file():
        return None
    return candidate


def handbook_sections(root: Path = ROOT) -> list[tuple[str, str, Path]]:
    """(chapter directory, section title, path) for every handbook section, in numeric order."""
    out = []
    chapters = sorted((root / "handbook").glob("ch*"), key=lambda p: int(re.findall(r"\d+", p.name)[0]))
    for chapter in chapters:
        files = sorted(chapter.glob("*.md"), key=lambda p: [int(x) for x in re.findall(r"\d+", p.stem)[:2]])
        for f in files:
            title = f.read_text().splitlines()[0].lstrip("# ").replace(" — ", " ").strip()
            out.append((chapter.name, title, f))
    return out
