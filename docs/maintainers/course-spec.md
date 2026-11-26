---
title: "Course specification (12-week course)"
parent: Maintainers
nav_order: 0
---

# Course specification: the 12-week course

Every lesson, lab, grader and tool guide of the main course follows this page. The week plan, notebook
names and tool guides are in [`curriculum.json`](https://github.com/berdakh/mlengineering/blob/main/curriculum.json).

## 1. Who the student is

* Has taken one introductory machine-learning course (for example Caltech's *Learning from Data*): knows
  training vs test error, overfitting, regularisation, validation, linear and logistic models, the bias-variance
  idea and the VC intuition. Has trained a model in a notebook.
* Programs in basic Python (variables, loops, functions, lists and dicts, a little NumPy).
* Has **never** used: SQL, a relational database, pandas beyond `read_csv`, the terminal beyond copying a
  command, Git, pytest, packaging, logging, APIs/HTTP, Docker, CI, cloud services, monitoring.
* Studies alone, at their own pace, 6-8 hours a week, mostly in **Google Colab**; Weeks 10-11 also use
  **VS Code** on their own computer (Linux, macOS or Windows).

Never assume a research background, a specific field, or a specific operating system. Write for a smart
beginner: define every term the first time, show before telling, and never skip a step that a beginner
would have to look up.

## 2. The teaching pattern (every lesson notebook)

A lesson is **75-120 minutes** of work, made of 4-6 short sections. Each section is:

1. **Why** — 2-4 sentences: the problem this solves on the job, in concrete terms.
2. **Idea** — the concept in plain language, with a small picture (a diagram or a tiny table) where it helps.
   Keep one idea per section. At most ~350 words of prose before the student types something.
3. **See it** — a runnable worked example in a code cell, with the expected output described.
4. **Try it** — a small ungraded cell the student edits immediately (change a value, predict the output first).
5. **Exercise** — 1-2 graded exercises per section (see §4), easiest first, each with a plain-language task,
   the expected shape of the answer, and a grader cell.

Then, at the end of every lesson:

* **Quiz** — 4-6 multiple-choice questions (`quiz("wNN.qK", answer)`), testing understanding, not recall.
  Every wrong option has an explanation of the misconception it represents.
* **Recap** — 5-8 bullet points: what you can now do.
* **On the job** — one paragraph: where this shows up in an ML engineer's week.
* **Going further** — links to the tool guide, the handbook (deep dives) and the advanced track, optional.

Connecting to theory: whenever a lesson touches modelling, connect it explicitly to what an intro-ML student
already knows (E_in vs E_out, the test set as a one-time estimate, overfitting, validation), then show what
changes with real, messy data. One sentence of the form "In *Learning from Data* terms, ..." is the pattern.
Do not quote or reproduce material from that course; refer to the ideas.

## 3. Labs (one per week)

A lab is a **graded programming assignment** of 90-120 minutes: 5-8 exercises that combine the week's lessons
on one realistic task, building up step by step (each exercise uses the previous one's result). No new
concepts in a lab. It ends with a short reflection prompt and "what to show in your portfolio".
Project milestones (notebooks 28, 36, 44) are labs on the SKAB project (see `docs/guides/project.md`).

## 4. Graded exercises

* Source format: `notebook_src/NN_name.py` (percent format). Put the solution between
  `### BEGIN SOLUTION` and `### END SOLUTION`; optionally add `### STARTER` lines (what the student sees).
  `python tools/nbbuild.py NN` builds `notebooks/NN_name.ipynb` (student) and
  `solutions/notebooks/NN_name.ipynb` (solved).
* Exercise shapes that work in Colab: a **function** to complete; a **SQL string** (`query = """..."""`); a
  **variable** to compute (a DataFrame, a number, a fitted pipeline); a **file** written with `%%writefile`
  then imported; **tests** the student writes, graded by running them against correct and buggy code.
* The cell after an exercise is always the grader: `grade("wNN.short_name", answer)`.
* Tests live in `src/mlcourse/graders/wNN.py` using `@exercise("wNN.name", hint="...")` and
  `register_quiz(...)`. A test raises `AssertionError("plain-language reason")`. Rules:
  - check **behaviour on several inputs**, including edge cases (empty, NULL, ties), never one exact
    implementation or one exact query text;
  - for SQL, run the student's query against `data/course/*.db` and compare the result to the expected
    result computed independently (pandas or a reference query), order-insensitive unless ORDER BY was asked;
    where possible also run against a second, freshly generated database so hard-coded answers fail;
  - failure messages explain *what* is wrong ("3 rows expected, got 5: are you counting cancelled orders?"),
    never the solution;
  - fast (under 2 s per exercise) and offline.
* Quizzes: `register_quiz("wNN.qK", "b", "why b is right", {"a": "why a is wrong", ...})`.

## 5. Notebook layout

```
[markdown] Colab badge + "Click the badge to run this notebook in Google Colab..."   (exact first cell)
[markdown] # NN · Title
           **Week W · lesson | lab · about X minutes**
           What you will learn (3-5 bullets) · What you need (previous notebooks) · How grading works (1 line)
[code]     setup cell (standard; see notebook 01; clones the repo in Colab, finds REPO_ROOT, imports grader)
... sections ...
[markdown] ## Quiz ... [code] quiz cells
[markdown] ## Recap / On the job / Going further
[code]     progress cell: from mlcourse.progress import mark ... (commented examples)
```

The standard setup cell (copy exactly; change nothing but the comment if needed):

```python
# --- Setup: works in Google Colab AND on your own computer. Safe to re-run. ---
# In Colab this downloads the course (about 30 s) and installs what it needs (about a minute, once
# per session). On your computer it just finds the course folder.
import os, sys, subprocess
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/mlengineering").exists():
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/berdakh/mlengineering.git", "/content/mlengineering"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                    "/content/mlengineering/requirements.txt"], check=True)
REPO_ROOT = Path("/content/mlengineering") if "google.colab" in sys.modules else next(
    p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
from mlcourse.grader import grade, quiz
print("Ready. Course folder:", REPO_ROOT)
```

Diagrams: Mermaid sources in `docs/assets/diagrams/src/mmd-cNN-KK.mmd` (rendered with `make diagrams`), shown
with `<img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-cNN-KK.svg"
alt="..." style="max-width:100%">`. Aim for 2-4 diagrams per lesson. Plots are produced live by code cells.
Maths: `$x$` inline in notebooks.

## 6. Tool guides (`docs/tools/<guide>.md`)

Each tool introduced in a week gets a self-contained reference chapter written for a beginner: what the tool is
and why teams use it; installing/opening it (Colab and local); the 20% of features used 80% of the time, each
with a short example; common errors and how to read them; a one-page cheat sheet; where to go next (official
docs). Front matter: `title`, `parent: Tool guides`, `nav_order`. 1,500-3,500 words.

## 7. Data

* `data/course/shop.db` — synthetic online shop (customers, products, orders, order_items, payments,
  support_tickets), built by `data/course/make_shop.py`. Use it for SQL, pandas, and the churn/modelling thread.
* A week may add its own small generated dataset in `data/course/make_<name>.py` + output (< 2 MB, seeded,
  with `--check`). Label synthetic data as synthetic.
* The project uses SKAB (`python project/get_skab.py`, ~4 MB, GPL-3.0, never committed).

## 8. Quality bar (what "done" means for a notebook)

* `python tools/nbbuild.py NN` builds; `python tools/check_notebooks.py` passes;
* `python tools/verify_notebooks.py NN` passes: the solved copy passes every grader with no cell errors, the
  student copy fails every grader and only raises `NotImplementedError`;
* runs in Colab: no local paths, no services, no Docker (Weeks 10-11 lessons that need Docker or VS Code say so
  at the top and keep their graded parts runnable in Colab, e.g. by checking a Dockerfile's contents);
* a beginner can follow it without searching the web; every term defined; every command explained.
