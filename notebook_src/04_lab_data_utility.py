# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/04_lab_data_utility.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 04 · Lab: a small, tested data utility
#
# **Week 1 · lab · about 90 minutes**
#
# A teammate sends you `customers.csv` every week, and every week something is wrong with it: a blank name, an
# age typed as text, an impossible date, the same customer twice. Before anyone trains a model on it, you will build
# a **CSV validator**: a small Python module that reads the file, checks it against a schema, and writes a report
# listing every problem. Then you put it under version control with Git.
#
# **What you will practise** (no new concepts, only this week's)
#
# - Functions with clear contracts, built and graded one at a time ([02](02_python_for_engineers.ipynb)).
# - Exceptions, dictionaries, the `csv` and `json` modules, `pathlib` ([02](02_python_for_engineers.ipynb)).
# - Shell commands and Git commits ([03](03_terminal_and_git.ipynb)).
#
# **What you need:** notebooks 01-03.
#
# **How grading works:** each function is graded on several small CSV files the grader creates itself, not just on
# the file you see here. Every exercise uses the one before it, so do them in order.

# %%
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

# %% [markdown]
# ## The data and the schema
#
# The next cell writes this week's file (synthetic: invented customers) to `/tmp/lab-data/customers.csv`. Look at it
# with the shell before writing any code; spotting problems by eye first tells you what the code must find.

# %%
import csv, json
from datetime import date

lab_data = Path("/tmp/lab-data")
lab_data.mkdir(parents=True, exist_ok=True)
(lab_data / "customers.csv").write_text(
    "id,name,age,signup_date\n"
    "101,Aru,31,2024-03-01\n"
    "102,Timur,45,2023-11-20\n"
    "103,,29,2024-01-15\n"
    "104,Dana,abc,2024-01-05\n"
    "105,Saule,38,2024-02-30\n"
    "102,Ali,22,2024-04-11\n"
    "106,Marat,,2024-05-02\n"
    "107,Zhanna,27,2024-05-19\n"
    "108,Erlan,52,2024-06-01\n"
    "109,Aigerim,34,2024-06-14\n"
)
!cat /tmp/lab-data/customers.csv

# %% [markdown]
# **Try it.** Before reading on, list the problems you can see. (There are five.)
#
# The **schema** says what each column must contain. We write it as a dictionary from column name to type:

# %%
SCHEMA = {"id": "int", "name": "str", "age": "int", "signup_date": "date"}
KEY = "id"   # the column that must be unique: one row per customer

# %% [markdown]
# Rules the validator applies:
#
# | Check | A problem when... |
# |---|---|
# | **missing** | a schema column is empty (or only spaces) |
# | **type** | a non-empty value cannot be read as its type: `int` (whole number), `date` (`YYYY-MM-DD`, a real calendar day); `str` accepts anything |
# | **duplicate** | the key column repeats a value seen in an earlier row |
#
# **Row numbers** count data rows from 1, so row 1 is the first line after the header (in a spreadsheet it would be
# line 2). Every function below uses this numbering.
#
# ## Step 1. Load the rows
#
# **Exercise 1.** Write `load_rows(path)`: return the rows of a CSV file as a list of dictionaries of strings, keyed
# by the header. A file with only a header gives `[]`.

# %%
def load_rows(path) -> list[dict[str, str]]:
    """Read a CSV file into a list of row dictionaries (all values are strings)."""
    ### BEGIN SOLUTION
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
    ### END SOLUTION

# %%
grade("w01.lab_load_rows", load_rows)

# %%
rows = load_rows(lab_data / "customers.csv")
print(len(rows), "rows; first:", rows[0])

# %% [markdown]
# ## Step 2. Missing values
#
# **Exercise 2.** Write `missing_values(rows, columns)`: a list of `(row_number, column)` pairs for every value in the
# given columns that is empty after `.strip()`. Check only the columns you are given.

# %%
def missing_values(rows: list[dict[str, str]], columns: list[str]) -> list[tuple[int, str]]:
    """(row number, column) for every empty value in the given columns; rows count from 1."""
    ### BEGIN SOLUTION
    problems = []
    for number, row in enumerate(rows, start=1):
        for column in columns:
            if (row.get(column) or "").strip() == "":
                problems.append((number, column))
    return problems
    ### END SOLUTION

# %%
grade("w01.lab_missing", missing_values)

# %%
missing_values(load_rows(lab_data / "customers.csv"), list(SCHEMA))

# %% [markdown]
# ## Step 3. Type problems
#
# **Exercise 3.** Write `type_problems(rows, schema)`: a list of `(row_number, column)` pairs for every **non-empty**
# value that does not fit its type (empty values are step 2's job, so skip them here).
#
# - `"int"`: `int(value)` must succeed, so `"4.5"` and `"abc"` are problems.
# - `"date"`: `date.fromisoformat(value)` must succeed, so `"2024-13-01"` and `"2023-02-29"` (not a leap year) are
#   problems.
# - `"str"`: always fine.
#
# Both conversions raise `ValueError` on bad input; catch it (lesson 02, section 2).

# %%
def type_problems(rows: list[dict[str, str]], schema: dict[str, str]) -> list[tuple[int, str]]:
    """(row number, column) for every non-empty value that does not match its schema type."""
    ### BEGIN SOLUTION
    problems = []
    for number, row in enumerate(rows, start=1):
        for column, kind in schema.items():
            value = (row.get(column) or "").strip()
            if value == "" or kind == "str":
                continue
            try:
                if kind == "int":
                    int(value)
                elif kind == "date":
                    date.fromisoformat(value)
            except ValueError:
                problems.append((number, column))
    return problems
    ### END SOLUTION

# %%
grade("w01.lab_type_problems", type_problems)

# %%
type_problems(load_rows(lab_data / "customers.csv"), SCHEMA)

# %% [markdown]
# ## Step 4. Duplicate keys
#
# **Exercise 4.** Write `duplicates(rows, key)`: a list of `(row_number, value)` pairs for every row whose `key`
# value already appeared in an earlier row. The first occurrence is not a problem; every later one is. A dictionary
# from value to the first row number where you saw it is all you need.

# %%
def duplicates(rows: list[dict[str, str]], key: str) -> list[tuple[int, str]]:
    """(row number, value) for every repeat of a key value after its first occurrence."""
    ### BEGIN SOLUTION
    first_seen: dict[str, int] = {}
    repeats = []
    for number, row in enumerate(rows, start=1):
        value = row.get(key, "")
        if value in first_seen:
            repeats.append((number, value))
        else:
            first_seen[value] = number
    return repeats
    ### END SOLUTION

# %%
grade("w01.lab_duplicates", duplicates)

# %%
duplicates(load_rows(lab_data / "customers.csv"), KEY)

# %% [markdown]
# ## Step 5. One report
#
# **Exercise 5.** Write `validate(path, schema, key)`, which combines steps 1-4 and returns a **report** dictionary:
#
# ```python
# {
#     "rows": 10,                 # number of data rows
#     "ok": False,                # True only if there are no problems at all
#     "problems": [
#         {"kind": "missing",   "row": 3, "column": "name"},
#         {"kind": "type",      "row": 4, "column": "age", "value": "abc"},
#         {"kind": "duplicate", "row": 6, "column": "id",  "value": "102"},
#         ...
#     ],
# }
# ```
#
# Every problem has at least the keys `kind` (`"missing"`, `"type"` or `"duplicate"`), `row` and `column`; extra keys
# such as `value` help whoever reads the report. Missing values are checked in every schema column.

# %%
def validate(path, schema: dict[str, str], key: str) -> dict:
    """Validate a CSV file against a schema and a unique key; return a report dictionary."""
    ### BEGIN SOLUTION
    rows = load_rows(path)
    problems = []
    for number, column in missing_values(rows, list(schema)):
        problems.append({"kind": "missing", "row": number, "column": column})
    for number, column in type_problems(rows, schema):
        problems.append({"kind": "type", "row": number, "column": column,
                         "value": rows[number - 1][column], "expected": schema[column]})
    for number, value in duplicates(rows, key):
        problems.append({"kind": "duplicate", "row": number, "column": key, "value": value})
    problems.sort(key=lambda p: (p["row"], p["column"]))
    return {"rows": len(rows), "ok": not problems, "problems": problems}
    ### END SOLUTION

# %%
grade("w01.lab_validate", validate)

# %%
report = validate(lab_data / "customers.csv", SCHEMA, KEY)
print("rows:", report["rows"], "ok:", report["ok"])
for problem in report["problems"]:
    print(problem)

# %% [markdown]
# Compare with the list you made by eye at the start. Did the code find something you missed, or the other way round?
#
# ## Step 6. Save the report
#
# **Exercise 6.** Write `write_report(report, path)`: save the report as indented JSON (`indent=2`), creating the parent
# folder if it does not exist (`Path(path).parent.mkdir(parents=True, exist_ok=True)`).

# %%
def write_report(report: dict, path) -> None:
    """Write the report to path as indented JSON, creating folders as needed."""
    ### BEGIN SOLUTION
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ### END SOLUTION

# %%
grade("w01.lab_report", write_report)

# %%
write_report(validate(lab_data / "customers.csv", SCHEMA, KEY), lab_data / "reports" / "customers.json")
!head -n 12 /tmp/lab-data/reports/customers.json

# %% [markdown]
# ## Step 7. Turn it into a module and commit it
#
# Functions inside a notebook are hard to reuse. The next cell copies your five functions (and `write_report`) into
# a file, `validator.py`, in a fresh folder `/tmp/lab-repo`, together with the imports they need and a `.gitignore`
# that keeps reports and data out of Git. `inspect.getsource` returns the source code of a function you defined.

# %%
import inspect

lab_repo = Path("/tmp/lab-repo")
subprocess.run(["rm", "-rf", str(lab_repo)])
lab_repo.mkdir(parents=True)
header = '"""Validate a CSV file against a simple schema. Week 1 lab."""\nimport csv\nimport json\nfrom datetime import date\nfrom pathlib import Path\n'
parts = [inspect.getsource(f) for f in (load_rows, missing_values, type_problems, duplicates, validate, write_report)]
(lab_repo / "validator.py").write_text(header + "\n\n" + "\n\n".join(parts))
(lab_repo / ".gitignore").write_text("reports/\ndata/\n__pycache__/\n")
!ls -a /tmp/lab-repo
!head -n 12 /tmp/lab-repo/validator.py

# %% [markdown]
# **Exercise 7, part 1.** Make `/tmp/lab-repo` a Git repository (main branch `main`, a repo-local name and email as
# in lesson 03) and commit `validator.py` and `.gitignore` with a clear message.

# %%
### BEGIN SOLUTION
!cd /tmp/lab-repo && git init -b main
!cd /tmp/lab-repo && git config user.name "Course Student"
!cd /tmp/lab-repo && git config user.email "student@example.com"
!cd /tmp/lab-repo && git add validator.py .gitignore
!cd /tmp/lab-repo && git commit -m "Add CSV validator, first version"
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %% [markdown]
# Next, make the module runnable from the terminal. The block under `if __name__ == "__main__":` runs only when the
# file is executed as a script (`python validator.py file.csv`), not when it is imported. `sys.argv[1]` is the first
# word after the script name. `sys.exit(1)` ends the program with **exit code** 1: by convention 0 means success and
# anything else means failure, which is how scripts, schedulers and CI systems (week 10) know a check failed.

# %%
cli = '''

if __name__ == "__main__":
    import sys
    schema = {"id": "int", "name": "str", "age": "int", "signup_date": "date"}
    report = validate(sys.argv[1], schema, "id")
    write_report(report, Path("reports") / "report.json")
    print(f"{report['rows']} rows, {len(report['problems'])} problem(s), report in reports/report.json")
    sys.exit(0 if report["ok"] else 1)
'''
with open(lab_repo / "validator.py", "a") as f:
    f.write(cli)
!cd /tmp/lab-repo && python validator.py /tmp/lab-data/customers.csv; echo "exit code: $?"
!cd /tmp/lab-repo && git status --short

# %% [markdown]
# The script prints `10 rows, 5 problem(s), ...` and `exit code: 1` (the file has problems; `$?` is the shell's name for the
# exit code of the last command). `git status --short` shows ` M validator.py` (modified) but not the new `reports/`
# folder: the `.gitignore` is doing its job.
#
# **Exercise 7, part 2.** Look at the change with `git diff`, then commit it. The repository should end clean, with
# two commits.

# %%
### BEGIN SOLUTION
!cd /tmp/lab-repo && git diff --stat
!cd /tmp/lab-repo && git add validator.py && git commit -m "Add command-line entry point"
!cd /tmp/lab-repo && git log --oneline
!cd /tmp/lab-repo && git status --short
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %%
grade("w01.lab_repo", "/tmp/lab-repo")

# %% [markdown]
# ## Quiz

# %% [markdown]
# **Q1.** Why validate a data file at the very start of a pipeline?
#
# - a. It makes the rest of the code run faster.
# - b. It replaces the need for tests of your code.
# - c. Bad input becomes a clear report now, instead of a confusing error later or a silently wrong model.
# - d. Once validated, bad rows no longer need handling.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.04_q1", answer)

# %% [markdown]
# **Q2.** Which design is most useful for a validator?
#
# - a. Return a list of all problems, so the caller can decide what to do.
# - b. Print each problem and return nothing.
# - c. Fix bad values silently, for example replace a blank age with 0.
# - d. Raise an exception at the first problem found.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.04_q2", answer)

# %% [markdown]
# **Q3.** Why build the validator from five small functions instead of one long one?
#
# - a. Small functions run faster.
# - b. Python limits how long a function can be.
# - c. Only because the graders need separate functions.
# - d. Each piece can be tested, reused and changed on its own, and `validate` just combines them.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.04_q3", answer)

# %% [markdown]
# **Q4.** Which statement about the lab repository is true?
#
# - a. The data files and generated reports should be committed along with the code.
# - b. The code and `.gitignore` are committed, data and reports are ignored, and the history lets you return to the first version.
# - c. Committing `validator.py` runs it to check that it works.
# - d. After `git commit`, the code is backed up on GitHub.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.04_q4", answer)

# %% [markdown]
# ## Reflection
#
# Write three or four sentences in a text cell of your own copy (or in your notes):
#
# - Which problem in `customers.csv` would have caused the most damage if nobody had caught it? Why?
# - One more check you would add (an age range? a date not in the future?), and which function it belongs in.
#
# ## What to show in your portfolio
#
# A small repository with `validator.py`, a README that shows the command and a sample report, and two or three
# commits with clear messages. Week 8 adds pytest tests to code like this; week 10 runs them automatically on every
# push. You will be able to push it to GitHub from your own computer then (see the
# [Git and GitHub guide](../docs/tools/git-github.md)).
#
# ## Recap
#
# - You turned a vague worry ("the file is often wrong") into explicit, testable rules: a schema and a key.
# - Each check is a small function with one job; `validate` combines them into one report.
# - The report is data (JSON), so programs can act on it, and the exit code tells scripts whether it passed.
# - The code is a module under version control, with data and outputs ignored.
#
# ## On the job
#
# Data validation is the first stage of most production ML pipelines. Teams use libraries for it (pandera,
# Great Expectations, pydantic, which you will meet in week 9), but they all do what you just built: a schema, a list
# of checks, a report, and a non-zero exit code that stops the pipeline before a bad file trains a model.
#
# ## Going further
#
# - Tool guide: [Python for engineers](../docs/tools/python-for-engineers.md).
# - Next week: [Week 2 · SQL from zero](../docs/weeks/week-2.md).

# %%
from mlcourse.progress import mark

# mark("04", "reading")
# mark("04", "independent")
