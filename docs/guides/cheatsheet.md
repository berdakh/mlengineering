---
title: Cheat sheet
parent: Guides
nav_order: 5
---

# Cheat sheet

## Every day

| Do | Command |
|---|---|
| What to study next | `python wb.py next` |
| All sessions and your flags | `python wb.py status` |
| Check your lab / challenge | `python wb.py check w3d4` · `python wb.py check w3d4 --challenge` |
| Record progress | `python wb.py mark w3d4 reading` (flags: `reading`, `guided`, `independent`, `review`) |
| Clear a flag | `python wb.py mark w3d4 review off` |
| Dated note | `python wb.py note w3d4 "what tripped me up"` |
| Open a notebook | `jupyter lab notebooks/16_point_vs_event_evaluation.ipynb` |
| Study app | `streamlit run app/study_app.py` |

Inside a notebook the same things are Python calls:

```python
from mlcourse.checks import check
from mlcourse.progress import mark, note, status

check("w3d4")                  # guided lab
check("w3d4", challenge=True)  # independent challenge
mark("w3d4", "guided")
```

Session ids: `w<week>d<day>`, e.g. `w3d4` is week 3, day 4, notebook 16. The
[full schedule](schedule.html) lists them all.

## Where things live

| Path | What |
|---|---|
| `notebooks/` | One notebook per core session (built from `notebook_src/`) |
| `labs/<session>/` | Lab and challenge starters you edit, worked-example scripts, data, checks |
| `diagnostic/` | The diagnostic sections (notebooks 01-02) |
| `solutions/` | Reference solutions, model answers, exercise and checkpoint answers. Attempt first |
| `docs/` | This site: weeks, handbook, guides |
| `interview/` | Interview prompt sets and their test harnesses |
| `progress/` | Your flags (`progress.json`), notes and skills ledger. Commit them |

## Maintenance (`make help` lists all)

| `make test` | course tests: helpers, tools, site markup |
| `make notebooks` | rebuild `notebooks/*.ipynb` from `notebook_src/*.py` |
| `make pages` | render notebooks into site pages |
| `make diagrams` | render Mermaid sources into SVGs (needs Node + Playwright) |
| `make check` | everything CI checks, without the long lab verification |
| `make verify` | every reference solution passes and every wrong submission is rejected (about 30 min) |
