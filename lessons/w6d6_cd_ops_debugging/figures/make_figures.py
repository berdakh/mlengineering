"""Regenerate the data figures of lesson w6d6 from committed recordings (no Docker needed).

    python lessons/w6d6_cd_ops_debugging/figures/make_figures.py

Inputs, written by the author-side replay
solutions/lessons/w6d6_cd_ops_debugging/record/record_incidents.py (which runs Docker, ~2 minutes):
  incident_timeline.csv  production /readyz status polled every 0.25 s (0 = no answer)
  incident_events.csv    what the replay did, and when
  incident_history.json  ops/state/releases.json at the end of the replay
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

LEVEL = {200: 2, 503: 1, 0: 0}
COLOUR = {200: STATUS["good"], 503: STATUS["warning"], 0: STATUS["critical"]}
SHORT = {"promote A": "promote A", "promote B": "promote B", "scenario 2 (bad promotion)": "incident: bad promotion",
         "rollback": "rollback", "scenario 1 (config)": "incident: MODEL_DIR",
         "fix config, redeploy same digest": "revert config", "scenario 3 (memory)": "incident: memory",
         "fix memory, redeploy same digest": "revert memory"}


def load():
    tl = [(float(r["t_seconds"]), int(r["readyz_status"])) for r in csv.DictReader(open(HERE / "incident_timeline.csv"))]
    ev = [(float(r["t_seconds"]), r["event"]) for r in csv.DictReader(open(HERE / "incident_events.csv"))]
    return tl, ev


def timeline(tl, ev) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for (t0, s0), (t1, _) in zip(tl, tl[1:]):
        ax.plot([t0, t1], [LEVEL[s0], LEVEL[s0]], color=COLOUR[s0], lw=6, solid_capstyle="butt")
    for t, name in ev:
        if name in SHORT:
            ax.axvline(t, color=INK["muted"], lw=0.8, ls=":")
            ax.text(t + 0.6, 2.35, SHORT[name], rotation=90, va="bottom", ha="left", fontsize=7.5, color=INK["secondary"])
    ax.set_yticks([0, 1, 2], ["no answer", "503 not ready", "200 ready"])
    ax.set_ylim(-0.5, 4.4)
    ax.set_xlim(0, tl[-1][0])
    ax.set_xlabel("seconds since the replay started (production /readyz, polled every 0.25 s)")
    ax.set_title("Production readiness through three incidents: two fail loudly, one fails late")
    save(fig, HERE / "readiness_timeline.svg")


def history() -> None:
    entries = json.loads((HERE / "incident_history.json").read_text())
    t0 = datetime.fromisoformat(entries[0]["deployed_at"])
    colour = {"good": STATUS["good"], "failed": STATUS["critical"], "rolled_back": STATUS["warning"]}
    fig, ax = plt.subplots(figsize=(8, 2.6))
    seen = set()
    for e in entries:
        x = (datetime.fromisoformat(e["deployed_at"]) - t0).total_seconds()
        y = 1 if e["env"] == "production" else 0
        ax.scatter(x, y, s=110, color=colour[e["status"]], zorder=3,
                   label=e["status"].replace("_", " ") if e["status"] not in seen else None)
        seen.add(e["status"])
        ax.text(x, y + 0.22, e["release"][:6], ha="center", fontsize=7.5, color=INK["secondary"])
    ax.set_yticks([0, 1], ["staging", "production"])
    ax.set_ylim(-0.5, 1.7)
    ax.set_xlabel("seconds after the first deployment (labels: first 6 characters of the release)")
    ax.legend(loc="lower right", ncols=3, fontsize=8)
    ax.set_title("Every deployment is a history entry; rollback = the last good entry with another digest")
    save(fig, HERE / "deployment_history.svg")


def downtime(tl, ev) -> None:
    starts = {n: t for t, n in ev}
    windows = [("bad promotion\n(fix: rollback)", "scenario 2 (bad promotion)", "scenario 1 (config)"),
               ("wrong MODEL_DIR\n(fix: revert config)", "scenario 1 (config)", "scenario 3 (memory)"),
               ("memory 64m\n(fix: revert limit)", "scenario 3 (memory)", "end")]
    names, bad = [], []
    for label, a, b in windows:
        pts = [(t, s) for t, s in tl if starts[a] <= t < starts[b]]
        secs = sum(t1 - t0 for (t0, s0), (t1, _) in zip(pts, pts[1:]) if s0 != 200)
        names.append(label)
        bad.append(secs)
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.barh(names[::-1], bad[::-1], color=SERIES[0], height=0.55)
    for y, v in enumerate(bad[::-1]):
        ax.text(v + 0.5, y, f"{v:.0f} s", va="center", color=INK["secondary"], fontsize=9)
    ax.set_xlabel("seconds production was not ready, from the incident to recovery")
    ax.set_xlim(0, max(bad) * 1.25)
    ax.set_title("Scripted replay: 13-20 s not ready per incident; human diagnosis time not included")
    save(fig, HERE / "time_not_ready.svg")
    with open(HERE / "time_not_ready.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["incident", "seconds_not_ready"])
        w.writerows([(n.replace("\n", " "), round(b, 1)) for n, b in zip(names, bad)])


if __name__ == "__main__":
    tl, ev = load()
    timeline(tl, ev)
    history()
    downtime(tl, ev)
    print("wrote readiness_timeline.svg, deployment_history.svg, time_not_ready.svg (+ time_not_ready.csv)")
