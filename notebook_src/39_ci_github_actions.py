# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/39_ci_github_actions.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 39 · Continuous integration with GitHub Actions
#
# **Week 10 · lesson · about 90 minutes**
#
# Tests only protect you if they run. **Continuous integration (CI)** runs them for you, on a clean machine, every
# time anyone pushes a commit or opens a pull request, and puts a green check or a red cross next to the change.
# This notebook teaches GitHub Actions, the CI service built into GitHub, by reading and writing its workflow files.
#
# **Where things run.** Workflows run on GitHub's machines, not in Colab. Every **graded** exercise here works on
# workflow text (YAML) and on test logs, so it runs in Colab. Seeing a workflow run happens **💻 on GitHub**, with a
# repository of your own, at the end.
#
# **What you will learn**
#
# - what CI is and what happens, step by step, after `git push`;
# - the anatomy of a workflow file and the YAML you need to read and write it (including two traps);
# - a workflow that installs your pinned dependencies and runs pytest on push and pull request;
# - a test matrix over Python versions, pip caching, read-only permissions and timeouts;
# - how to read a failed run, and how to keep secrets out of logs.
#
# **What you need:** notebook 30 (pytest), notebook 37 (requirements files) and notebook 03 (Git).
#
# **How grading works:** run the cell under each exercise; `grade(...)` checks your function or workflow on several
# cases and explains what is wrong without giving the answer away.

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
import re
import yaml
from mlcourse.graders.w10 import use, work_dir

WORK = work_dir()

# %% [markdown]
# ## 1 · What CI is
#
# **Why.** "Did you run the tests?" "Yes" (on a laptop with a different Python, an old package, and a file that was
# never committed). CI replaces that conversation with a rule: every change is tested the same way, on a fresh
# machine, before anyone merges it.
#
# **Idea.** You add a **workflow** file to your repository, in the folder `.github/workflows/`. When an **event**
# happens (a push, a pull request, a schedule, a button click), GitHub reads the file, starts a fresh virtual
# machine called a **runner**, and executes the steps it lists. Each step either succeeds or fails; the first
# failure stops the job and marks the commit with a red cross, and you get a log to read.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c39-01.svg" alt="A push triggers GitHub to start a fresh runner that checks out, sets up Python, installs and runs pytest, ending in a green check or a red cross" style="max-width:100%">
#
# The runner starts empty: none of your laptop's packages, files or settings are there. That is the point. If the
# tests pass on the runner, they pass because of what is in the repository, not because of your machine.
#
# GitHub Actions is free for public repositories; private ones get a monthly allowance of minutes, after which
# workflows stop (or are billed, if a payment method is set). Keep workflows short.
#
# **See it.** This course tests itself with GitHub Actions. Here are the first 40 lines of its workflow:

# %%
course_ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
print("\n".join(course_ci.splitlines()[:40]))

# %% [markdown]
# **Try it.** Find, in that file: the events that trigger it (`on:`), the name of the first job, the machine it
# runs on, and the first `run:` command. Which step makes sure the notebooks match their sources?

# %% [markdown]
# ## 2 · Workflow anatomy and just enough YAML
#
# **Why.** A workflow is a YAML file, and YAML has a few rules that, broken, produce confusing errors or, worse,
# silently different behaviour.
#
# **Idea.** YAML is a way to write nested dicts and lists as indented text:
#
# - `key: value` is a dict entry; indentation (spaces only, never tabs) nests one dict inside another;
# - a line starting with `- ` is a list item;
# - `run: |` starts a multi-line string: each following, more-indented line is one line of the shell script;
# - text needs no quotes, except when it could be read as something else (a number, `true`, or text containing
#   `: `).
#
# The parts of a workflow:
#
# | Key | Meaning |
# |---|---|
# | `name:` | the name shown on GitHub |
# | `on:` | the events that start it: `push`, `pull_request`, `schedule`, `workflow_dispatch` (a button) |
# | `permissions:` | what the run's automatic token may do (start with read-only) |
# | `jobs:` | one or more jobs; they run **in parallel** on separate runners unless one `needs:` another |
# | `runs-on:` | the machine type, usually `ubuntu-latest` |
# | `steps:` | the list a job runs in order; each is either `uses:` (a ready-made **action**, like `actions/checkout@v7`) or `run:` (shell commands) |
# | `with:` / `env:` | inputs for an action / environment variables for a step |
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c39-02.svg" alt="A workflow contains jobs; each job has steps; a matrix turns one job into parallel copies; needs orders jobs" style="max-width:100%">
#
# **Trap 1.** In YAML 1.1, which `yaml.safe_load` follows, the bare words `on`, `yes` and `true` mean the boolean
# `True`. GitHub reads `on:` correctly, but Python does not:

# %%
example = """name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: python -m pytest -q
"""
data = yaml.safe_load(example)
print(data)
print("keys:", list(data))

# %% [markdown]
# The key came back as `True`, not `"on"`. Any tool that reads workflows in Python must look for both.
#
# **Try it.** Change `on: [push, pull_request]` to `"on": [push, pull_request]` (with quotes) and run again.

# %% [markdown]
# ### Exercise 1 · which events start this workflow?
#
# Write `triggers(workflow_text)` returning the sorted list of event names. `on` can be a string (`on: push`), a
# list (`on: [push, pull_request]`) or a dict whose keys are the events (with settings, or empty, as values). Look
# the key up as `"on"` **and** as `True`. No `on` at all gives `[]`.

# %%
def triggers(workflow_text):
    ### BEGIN SOLUTION
    data = yaml.safe_load(workflow_text) or {}
    on = data.get("on", data.get(True))
    if on is None:
        return []
    if isinstance(on, str):
        return [on]
    return sorted(on)          # a list of names, or the keys of a dict
    ### END SOLUTION


# %%
grade("w10.triggers", triggers)

# %% [markdown]
# ### Exercise 2 · what does a job run?
#
# Write `job_commands(workflow_text, job)`: every shell command the job runs, in order. Take the steps of
# `jobs[job]`, keep those with a `run` key, split multi-line `run` text into lines, strip each line and drop empty
# ones. A job that does not exist, or has no `run` steps, gives `[]`.

# %%
def job_commands(workflow_text, job):
    ### BEGIN SOLUTION
    data = yaml.safe_load(workflow_text) or {}
    steps = (data.get("jobs", {}).get(job) or {}).get("steps") or []
    commands = []
    for step in steps:
        for line in str(step.get("run", "")).splitlines():
            if line.strip():
                commands.append(line.strip())
    return commands
    ### END SOLUTION


# %%
print(use(job_commands, course_ci, "site")[:4])
grade("w10.job_commands", job_commands)

# %% [markdown]
# ## 3 · A workflow that runs your tests
#
# **Why.** The most valuable workflow is also the simplest: on every push and pull request, install exactly the
# pinned dependencies and run the test suite.
#
# **Idea.** Four steps, in this order, because each needs the one before:
#
# 1. `uses: actions/checkout@v7` puts your repository's files on the runner (it starts empty);
# 2. `uses: actions/setup-python@v7` with `python-version: "3.12"` installs that Python;
# 3. `run: python -m pip install -r requirements.txt` installs your pinned dependencies;
# 4. `run: python -m pytest -q` runs the tests; a failing test makes pytest exit with a non-zero code, which fails
#    the step and the job.
#
# The `@v7` after an action is its **version**. Always pin it: an action is someone else's code running with access
# to your repository. (`@v7` was the current major version of both actions when this course was written; GitHub
# shows the latest on each action's page.)
#
# **Trap 2.** `python-version: 3.10` without quotes is the *number* 3.1 in YAML, and setup-python then looks for
# Python 3.1. Always quote versions: `"3.10"`.

# %% [markdown]
# ### Exercise 3 · your first workflow
#
# Write `.github/workflows/ci.yml` as a string: name it `CI`; run on `push` and `pull_request`; one job `test` on
# `ubuntu-latest` with the four steps above, in order (give the two `run` steps a `name:` each). The grader parses
# your YAML and checks the triggers, the runner, the steps and their order, the pinned action versions and the
# quoted Python version.

# %%
### BEGIN SOLUTION
workflow = """name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: python -m pip install -r requirements.txt
      - name: Run the tests
        run: python -m pytest -q
"""
### STARTER
workflow = """# YOUR WORKFLOW HERE
"""
### END SOLUTION

# %%
grade("w10.workflow", workflow)

# %% [markdown]
# ### Exercise 4 · catch the unquoted version
#
# Write `matrix_versions(workflow_text, job)` that returns the job's `strategy` → `matrix` → `python-version` list as
# strings, `[]` when the job has no matrix, and raises `ValueError` when any version was written without quotes
# (it arrives as a `float`, and `3.10` has already become `3.1`).

# %%
def matrix_versions(workflow_text, job):
    ### BEGIN SOLUTION
    data = yaml.safe_load(workflow_text) or {}
    job_data = data.get("jobs", {}).get(job) or {}
    versions = (job_data.get("strategy") or {}).get("matrix", {}).get("python-version", [])
    for v in versions:
        if isinstance(v, float):
            raise ValueError(f"python-version {v} is a number: put it in quotes")
    return [str(v) for v in versions]
    ### END SOLUTION


# %%
grade("w10.matrix_versions", matrix_versions)

# %% [markdown]
# ## 4 · A test matrix and a pip cache
#
# **Why.** Your laptop has one Python; your users and servers may have others. And installing the same packages on
# every run wastes a minute each time.
#
# **Idea.** A **matrix** runs copies of a job with different values, in parallel:
#
# ```yaml
#   test:
#     runs-on: ubuntu-latest
#     strategy:
#       fail-fast: false
#       matrix:
#         python-version: ["3.11", "3.12", "3.13"]
#     steps:
#       - uses: actions/checkout@v7
#       - uses: actions/setup-python@v7
#         with:
#           python-version: ${{ matrix.python-version }}
#           cache: pip
# ```
#
# `${{ ... }}` is an **expression**: GitHub fills in the current matrix value. `fail-fast: false` lets the other
# versions finish when one fails, so you see the whole picture. `cache: pip` saves pip's downloads between runs,
# keyed on your requirements files: the next run reuses them until the requirements change. This course's own CI
# uses a matrix too (scroll up to its `labs` job).

# %% [markdown]
# ### Exercise 5 · test three Python versions
#
# Start from your workflow of exercise 3 and add the matrix: Python `"3.11"`, `"3.12"` and `"3.13"`, `fail-fast:
# false`, setup-python using the matrix value, and `cache: pip`.

# %%
### BEGIN SOLUTION
workflow_matrix = """name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - name: Install dependencies
        run: python -m pip install -r requirements.txt
      - name: Run the tests
        run: python -m pytest -q
"""
### STARTER
workflow_matrix = """# YOUR WORKFLOW HERE
"""
### END SOLUTION

# %%
grade("w10.workflow_matrix", workflow_matrix)

# %% [markdown]
# ## 5 · Reading a failed run
#
# **Why.** A red cross is information, not an insult. The skill is to get from the cross to the cause in a minute.
#
# **Idea.** On GitHub: the **Actions** tab → the failed run → the red job → the first red step. The log of a pytest
# step looks exactly like pytest on your computer, with a timestamp in front of each line when you download it. Read
# it **top down to the first** `FAILED` or `ERROR` line: it names the test and the assertion. Then run that test
# locally (`python -m pytest tests/test_api.py::test_name`), fix it, push again. Do not just press *Re-run*: re-run
# only when you have evidence of a flaky outside cause (a network timeout), and never delete a failing test to get
# green.
#
# Two pytest outcomes to tell apart: **FAILED** means a test ran and an assertion failed; **ERROR** during
# collection means pytest could not even import the test file (often a missing dependency in `requirements.txt`,
# a classic "works on my machine" case that CI exists to catch).
#
# **See it.** A small project with a bug, tested for real right here. This is what the pytest step would print:

# %%
demo = WORK / "ci-demo"
(demo / "tests").mkdir(parents=True, exist_ok=True)
(demo / "pricing.py").write_text(
    "def discounted(total, percent):\n"
    "    return round(total * (1 - percent), 2)   # bug: percent is 0-100, not 0-1\n")
(demo / "tests" / "test_pricing.py").write_text(
    "from pricing import discounted\n\n"
    "def test_no_discount():\n    assert discounted(100, 0) == 100\n\n"
    "def test_ten_percent():\n    assert discounted(100, 10) == 90\n\n"
    "def test_rounding():\n    assert discounted(19.99, 15) == 16.99\n")
run = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider", "--rootdir", str(demo),
                      "-o", "pythonpath=."], cwd=demo, capture_output=True, text=True)
log = run.stdout
print(log[-1500:])
print("exit code:", run.returncode, "(non-zero fails the CI step)")

# %% [markdown]
# ### Exercise 6 · pull the failing tests out of a log
#
# Write `first_failures(log)`: the test ids from lines that **start** with `FAILED` or `ERROR`, in order, without
# duplicates. GitHub's downloaded logs put a timestamp such as `2026-11-26T10:00:00.1234567Z ` in front of each
# line: remove it first. The id is the first word after `FAILED`/`ERROR` (for collection errors it is just the
# file).

# %%
def first_failures(log):
    ### BEGIN SOLUTION
    ids = []
    for line in log.splitlines():
        line = re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z\s+", "", line.strip())
        match = re.match(r"^(FAILED|ERROR)\s+(\S+)", line)
        if match and match.group(2) not in ids:
            ids.append(match.group(2))
    return ids
    ### END SOLUTION


# %%
print(use(first_failures, log))
grade("w10.failures", first_failures)

# %% [markdown]
# **Branch protection.** CI only helps if a red cross blocks the merge. In a repository's **Settings → Branches →
# Add rule** for `main`, *Require status checks to pass before merging* and pick your workflow's job: GitHub then
# refuses to merge a pull request until it is green. Teams combine it with *Require a pull request before merging*,
# so nobody pushes straight to `main`.

# %% [markdown]
# ## 6 · Secrets, permissions and timeouts
#
# **Why.** A workflow runs code with access to your repository and, if you give it, to cloud accounts. A leaked
# token in a public log is a real incident, and a stuck job can burn a month of free minutes.
#
# **Idea.** Three habits.
#
# 1. **Secrets** (API keys, tokens) go in *Settings → Secrets and variables → Actions*, never in the repository.
#    Use them through `env:`, so the shell receives an environment variable and GitHub can mask the value in logs:
#
#    ```yaml
#          - name: Deploy
#            env:
#              DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
#            run: ./deploy.sh
#    ```
#
#    Writing `${{ secrets.DEPLOY_TOKEN }}` straight into `run:` pastes the value into the script text before it
#    runs; a typo, an `echo` or `set -x` prints it, and odd characters can break the command. Pull requests from
#    forks do not receive secrets at all, which protects you from strangers' code.
# 2. **Permissions.** Each run gets an automatic token. `permissions: contents: read` at the top limits it to
#    reading the code, enough for tests. Grant more (for example `packages: write` to push an image) only in the
#    job that needs it.
# 3. **Timeouts.** `timeout-minutes: 15` on a job stops a hung test from running for the default six hours.

# %% [markdown]
# ### Exercise 7 · spot the leaky steps
#
# Write `unsafe_secret_steps(workflow_text)`: for every job and every step whose `run` text contains
# `${{ secrets.` (any spaces after `{{`), report the step's `name`, or `"JOB step N"` (N counting from 1) when it
# has none. Secrets used through `env:` are fine and must not be reported.

# %%
def unsafe_secret_steps(workflow_text):
    ### BEGIN SOLUTION
    data = yaml.safe_load(workflow_text) or {}
    found = []
    for job_name, job in (data.get("jobs") or {}).items():
        for number, step in enumerate(job.get("steps") or [], start=1):
            if re.search(r"\$\{\{\s*secrets\.", str(step.get("run", ""))):
                found.append(step.get("name") or f"{job_name} step {number}")
    return found
    ### END SOLUTION


# %%
grade("w10.unsafe_secrets", unsafe_secret_steps)

# %% [markdown]
# ### Exercise 8 · harden your workflow
#
# Take your workflow from exercise 3 (or 5) and add `permissions:` with `contents: read` at the top level and
# `timeout-minutes: 15` to the job.

# %%
### BEGIN SOLUTION
workflow_hardened = """name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
      - name: Install dependencies
        run: python -m pip install -r requirements.txt
      - name: Run the tests
        run: python -m pytest -q
"""
### STARTER
workflow_hardened = """# YOUR WORKFLOW HERE
"""
### END SOLUTION

# %%
grade("w10.workflow_hardened", workflow_hardened)

# %% [markdown]
# ## 💻 On GitHub: watch your workflow run
#
# 1. On github.com, create a new **public** repository (public repositories get free Actions minutes), for example
#    `ci-practice`, and clone it (notebook 03).
# 2. Copy in the `ci-demo` folder's files from your working folder (`pricing.py`, `tests/`), add a
#    `requirements.txt` with the line `pytest==8.3.4` (any recent version, pinned), and save your hardened workflow
#    as `.github/workflows/ci.yml`.
# 3. `git add .`, `git commit -m "Add CI"`, `git push`. Open the **Actions** tab: the run appears within seconds and
#    fails on the pricing bug. Click through to the `FAILED` line.
# 4. Fix `discounted` (divide `percent` by 100), commit, push: a green check.
#
# Nothing here costs money or creates cloud resources. Keep the repository; the lab adds a Docker job to the same
# idea.

# %% [markdown]
# ## Quiz
#
# **Q1.** Your tests pass locally but the CI job fails with `No module named 'pandas'`. Why might that be? (a) the
# runner shares your laptop's `.venv` (b) each job starts on a fresh machine; pandas is installed only if your
# workflow installs it, e.g. from `requirements.txt`, and it is missing there (c) GitHub guesses the dependencies
# (d) a previous job's files should have been there

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.39_q1", answer)

# %% [markdown]
# **Q2.** Why write `python-version: "3.10"` with quotes? (a) quoted values are faster (b) GitHub rejects numbers
# (c) without quotes YAML reads the number 3.1, and setup-python looks for Python 3.1 (d) only 3.12 needs quotes

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.39_q2", answer)

# %% [markdown]
# **Q3.** A run is red. What is the best first move? (a) open the first red step and read down to the first
# `FAILED`/`ERROR` line, then reproduce that test locally (b) press Re-run until it is green (c) skip the failing
# test (d) read only the last line of the log

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.39_q3", answer)

# %% [markdown]
# **Q4.** What does CI plus branch protection give a team? (a) proof that the code is correct (b) no need to run
# tests locally (c) an automatic code review (d) a rule that nothing is merged into `main` unless its tests passed on
# a clean machine

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.39_q4", answer)

# %% [markdown]
# **Q5.** How should a workflow step use an API token? (a) commit it in a private repository (b) store it as a
# repository secret and pass it to the step through `env:` (c) share it with forks via pull requests (d) base64-encode
# it in the YAML

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w10.39_q5", answer)

# %% [markdown]
# ## Recap
#
# - CI runs your checks on a fresh machine for every push and pull request; the workflow lives in
#   `.github/workflows/*.yml`.
# - A workflow: `on` (events), `permissions`, `jobs` → `runs-on` → `steps` (`uses` an action, or `run` commands).
# - The core job: checkout, setup-python with a quoted version, `pip install -r requirements.txt`, `pytest`.
# - YAML traps: `on` loads as `True` in Python; unquoted `3.10` becomes `3.1`.
# - Matrix for several Python versions, `fail-fast: false`, `cache: pip`.
# - Read failures top down to the first `FAILED`/`ERROR`; reproduce locally; protect `main` with required checks.
# - Secrets through `env:`, read-only permissions, a timeout on every job.
#
# **On the job.** Every serious repository has CI, and changing it is ordinary work: adding a check, speeding up a
# slow job, fixing a red build on `main` (which the whole team waits on). In ML teams, CI often also runs data
# validation and a small training smoke test, and builds the service image, which is the lab's next step.
#
# **Going further.** The [GitHub Actions tool guide](../docs/tools/github-actions.md) has the full syntax you need,
# a cheat sheet and the common errors. Next: notebook 40, the lab: containerise the prediction API and add CI.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("39", "reading")
# mark("39", "guided")
