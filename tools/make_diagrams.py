#!/usr/bin/env python3
"""Render docs/assets/diagrams/src/*.mmd (Mermaid) into docs/assets/diagrams/*.svg.

Why static SVGs: notebooks are opened in Jupyter and Colab, and Colab does not draw
Mermaid. A static SVG shows up everywhere - GitHub, Jupyter, Colab and the course
site - so every diagram in the notebooks is an <img> of a file rendered here.

Rendering needs a headless browser (Playwright + Chromium) and the bundled Mermaid
build in app/static/mermaid.min.js (11.4.1, MIT). Checking does not: each SVG records
the SHA-256 of its source, and --check only compares hashes, so CI needs no browser.

    python tools/make_diagrams.py            # render new or changed diagrams
    python tools/make_diagrams.py --all      # re-render everything
    python tools/make_diagrams.py --check    # fail if any SVG is missing or stale
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "docs" / "assets" / "diagrams" / "src"
OUT = REPO_ROOT / "docs" / "assets" / "diagrams"
MERMAID = REPO_ROOT / "app" / "static" / "mermaid.min.js"
STAMP = re.compile(r"<!-- source-sha256: ([0-9a-f]{64}) -->")

RENDERER = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [mermaidPath, jobsPath] = process.argv.slice(2);
  const jobs = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent('<html><body></body></html>');
  await page.addScriptTag({ path: mermaidPath });
  await page.evaluate(() => mermaid.initialize({ startOnLoad: false, theme: 'neutral',
      securityLevel: 'strict', fontFamily: 'Helvetica, Arial, sans-serif',
      htmlLabels: false, flowchart: { htmlLabels: false } }));
  const failures = [];
  for (const job of jobs) {
    try {
      const svg = await page.evaluate(async ({ id, text }) =>
          (await mermaid.render(id, text)).svg, { id: 'd' + job.n, text: job.text });
      fs.writeFileSync(job.out, svg);
    } catch (e) { failures.push(job.name + ': ' + String(e).split('\n')[0]); }
  }
  await browser.close();
  if (failures.length) { console.error(failures.join('\n')); process.exit(1); }
})();
"""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def stamped(svg_path: Path) -> str | None:
    if not svg_path.is_file():
        return None
    m = STAMP.search(svg_path.read_text(encoding="utf-8")[:300])
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    sources = sorted(SRC.glob("*.mmd"))
    todo = [s for s in sources if args.all or stamped(OUT / f"{s.stem}.svg") != digest(s.read_text(encoding="utf-8"))]
    orphans = [p for p in OUT.glob("*.svg") if p.stem.startswith("mmd-") and not (SRC / f"{p.stem}.mmd").exists()]
    if args.check:
        for s in todo:
            print(f"stale or missing: {s.stem}.svg", file=sys.stderr)
        for p in orphans:
            print(f"orphan: {p.name}", file=sys.stderr)
        if todo or orphans:
            print("run `python tools/make_diagrams.py`", file=sys.stderr)
            return 1
        print(f"all {len(sources)} diagrams up to date")
        return 0
    for p in orphans:
        p.unlink()
    if not todo:
        print(f"all {len(sources)} diagrams up to date")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        jobs = [{"n": i, "name": s.stem, "text": s.read_text(encoding="utf-8"), "out": str(Path(tmp) / f"{s.stem}.svg")}
                for i, s in enumerate(todo)]
        (Path(tmp) / "jobs.json").write_text(json.dumps(jobs))
        (Path(tmp) / "render.js").write_text(RENDERER)
        proc = subprocess.run(["node", str(Path(tmp) / "render.js"), str(MERMAID), str(Path(tmp) / "jobs.json")],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
        for job in jobs:
            out = Path(job["out"])
            if out.is_file():
                svg = out.read_text(encoding="utf-8")
                (OUT / f"{job['name']}.svg").write_text(
                    f"<!-- source-sha256: {digest(job['text'])} -->\n{svg}\n", encoding="utf-8")
    print(f"rendered {len(todo)} diagram(s)")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
