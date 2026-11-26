---
title: Cheat sheet
parent: Guides
nav_order: 4
---

# Cheat sheet

## In every notebook

| Do | How |
|---|---|
| Start | Run the first code cell (setup). In Colab, wait for `Ready. Course folder: ...` |
| Grade an exercise | Run the cell under it: `grade("w02.cheap_products", query)` |
| Answer a quiz | Put a letter between the quotes, `answer = "b"`, then run `quiz("w02.05_q1", answer)` |
| Read a result | ✅ passed · ❌ what is wrong, with a hint · ⏳ not attempted yet |
| Start again | *Runtime → Restart session* (Colab) or *Restart* (VS Code / Jupyter), then run from the top |
| Check a solution | `solutions/notebooks/<same name>.ipynb`, after a real attempt |
| Record progress | `from mlcourse.progress import mark` then `mark("05", "guided")` |
| Add a note | `from mlcourse.progress import note` then `note("05", "what tripped me up")` |

Progress flags: `reading`, `guided` (you finished the exercises), `independent` (you did them without hints or
solutions), `review` (come back to this). They are stored in `progress/progress.json`; in Colab, download that
file if you want to keep it.

## Inside the course folder

| Path | What |
|---|---|
| `notebooks/` | The 48 notebooks you work in |
| `solutions/notebooks/` | The same notebooks, solved |
| `data/course/` | The synthetic shop database (`shop.db`) and other small course datasets |
| `src/mlcourse/` | `grader`, `sql` (`sql()`, `tables()`, `schema()`), `progress` |
| `docs/` | This site |

## Each tool's cheat sheet

Every tool guide ends with a one-page cheat sheet:
[Colab](../tools/colab.html) · [Python](../tools/python-for-engineers.html) · [terminal](../tools/terminal.html) ·
[Git](../tools/git-github.html) · [SQL](../tools/sql.html) · [pandas](../tools/pandas.html) ·
[matplotlib](../tools/matplotlib.html) · [scikit-learn](../tools/scikit-learn.html) ·
[packaging](../tools/packaging.html) · [pytest](../tools/pytest.html) · [FastAPI](../tools/fastapi.html) ·
[VS Code](../tools/vscode.html) · [Docker](../tools/docker.html) · [GitHub Actions](../tools/github-actions.html) ·
[AWS](../tools/cloud-aws.html) · [monitoring](../tools/monitoring.html)

## Maintainers (`make help` lists all)

| Command | Does |
|---|---|
| `python tools/nbbuild.py 05` | Build `notebooks/05_*.ipynb` and `solutions/notebooks/05_*.ipynb` from `notebook_src/` |
| `python tools/verify_notebooks.py 05` | Solved copy passes every grader; student copy fails them, only with `NotImplementedError` |
| `python tools/check_notebooks.py` | Valid JSON, code parses, links and images exist, Colab badges right |
| `python tools/check_links.py` | Every relative link in the repository resolves |
| `make diagrams` | Render Mermaid sources to SVG (needs Node and Playwright) |
| `python wb.py check <session>` | Advanced track: run one lab's checks |
