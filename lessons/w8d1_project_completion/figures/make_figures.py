"""Figures for w8d1. Run from the repository root:

    python lessons/w8d1_project_completion/figures/make_figures.py

1. audit_timeline.svg: REAL. Step durations of the clean-clone audit of the reference flowguard evaluation
   (read from the committed solutions/.../real_audit/REPRODUCTION_LOG.json).
2. findings_matrix.svg: SYNTHETIC repositories. The reference audit tool is run on the seven synthetic
   projects used by the checks; the matrix shows which finding codes each one produced.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE.parent / "checks")]
from tools.figstyle import INK, SEQUENTIAL, SERIES, apply, save  # noqa: E402

import synthetic_repo  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

rows_out = []
audit = json.loads((ROOT / "solutions/lessons/w8d1_project_completion/real_audit/REPRODUCTION_LOG.json").read_text())
steps = [(s["name"].split(" (")[0], s["seconds"]) for s in audit["steps"]]
setup = audit["total_seconds"] - sum(s for _, s in steps)
parts = [("clone, venv, pinned install", setup)] + steps
fig, ax = plt.subplots(figsize=(7.2, 2.6))
for i, (name, sec) in enumerate(parts):
    ax.barh(i, sec, color=SERIES[0] if "evaluate" in name else SEQUENTIAL[2], height=0.6)
    ax.text(sec + 0.8, i, f"{sec:.1f} s", va="center", fontsize=9, color=INK["secondary"])
    rows_out.append(["audit_timeline", name, f"{sec:.2f}"])
ax.set_yticks(range(len(parts)), [p[0] for p in parts])
ax.invert_yaxis()
ax.set_xlabel("seconds")
ax.set_xlim(0, max(s for _, s in parts) * 1.18)
ax.set_title(f"Real clean-clone audit: {audit['total_seconds']:.0f} s, {len(audit['headline'])} headline values, verdict {audit['verdict']}")
ax.grid(axis="y", visible=False)
save(fig, HERE / "audit_timeline.svg")

tool = ROOT / "solutions/lessons/w8d1_project_completion/lab/audit/clean_clone_check.py"
codes_order = ["absolute_path", "unpinned_requirement", "missing_dependency", "missing_file",
               "headline_mismatch", "nondeterministic", "step_failed"]
matrix = []
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    for v in synthetic_repo.VARIANTS:
        repo = synthetic_repo.make_repo(tmp / "repos", v)
        log = tmp / f"{v}.md"
        subprocess.run([sys.executable, str(tool), str(repo), "--log", str(log)], capture_output=True, text=True)
        found = {f["code"] for f in json.loads(log.with_suffix(".json").read_text())["findings"]}
        matrix.append([c in found for c in codes_order])
        rows_out.append(["findings_matrix", v, ";".join(sorted(found)) or "PASS"])
fig, ax = plt.subplots(figsize=(7.2, 3.4))
for i, row in enumerate(matrix):
    for j, hit in enumerate(row):
        ax.add_patch(plt.Rectangle((j - 0.45, i - 0.4), 0.9, 0.8, color=SERIES[1] if hit else INK["grid"], lw=0))
        if hit:
            ax.text(j, i, "✕", ha="center", va="center", color="#ffffff", fontsize=10)
ax.set_xlim(-0.5, len(codes_order) - 0.5)
ax.set_ylim(len(matrix) - 0.5, -0.5)
ax.set_xticks(range(len(codes_order)), [c.replace("_", "\n") for c in codes_order], fontsize=8)
ax.set_yticks(range(len(matrix)), [v.replace("_", " ") for v in synthetic_repo.VARIANTS])
ax.grid(False)
ax.set_title("SYNTHETIC projects: each defect produces its own finding; the good one none")
for side in ("left", "bottom"):
    ax.spines[side].set_visible(False)
ax.tick_params(length=0)
save(fig, HERE / "findings_matrix.svg")

with open(HERE / "figure_data.csv", "w", newline="") as fh:
    csv.writer(fh).writerows([["figure", "item", "value"]] + rows_out)
print("wrote audit_timeline.svg, findings_matrix.svg, figure_data.csv")
