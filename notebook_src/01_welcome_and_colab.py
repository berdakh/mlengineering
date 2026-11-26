# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/01_welcome_and_colab.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 01 · Welcome, Colab, and how this course works
#
# **Week 1 · lesson · about 75 minutes**
#
# You have studied machine learning: training and test error, overfitting, validation, linear and logistic
# models. This course teaches the other half of the job: getting data out of databases, writing code other
# people can trust, testing it, serving a model behind an API, shipping it in a container and keeping it
# healthy once real users depend on it.
#
# **What you will learn in this notebook**
#
# - How the 12 weeks fit together, and what a week looks like.
# - How Google Colab works: cells, the runtime, and where your files really live.
# - Why the *order* in which you run cells matters, and how to avoid the classic notebook trap.
# - How to save your work so a runtime reset does not erase it.
# - How graded exercises and quizzes work, and how to record your progress.
#
# **What you need:** a Google account and a web browser. Nothing to install.
#
# **How grading works:** after each exercise there is a grader cell. Run it and it tells you immediately
# whether your answer works, and if not, what to look at.

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
# ## 1. The course in one picture
#
# **Why.** A model that scores well in a notebook is not yet useful to anyone. Somebody has to fetch the
# data reliably, prove the score is honest, package the code, put it behind an API, run it somewhere and
# notice when it starts going wrong. Each week of this course adds one of those layers.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/roadmap.svg" alt="The twelve-week roadmap" style="max-width:100%">
#
# The roadmap image shows eight blocks of the original program; this 12-week course covers the same ground
# at a beginner's pace:
#
# | Weeks | Part | You learn to |
# |---|---|---|
# | 1 | Workbench | use Colab, write clean Python, use the terminal and Git |
# | 2-3 | Data | query databases with SQL, work with pandas, clean and check data |
# | 4-7 | Applied ML | build features and pipelines, frame problems, choose metrics, validate honestly, compare models |
# | 8-9 | Software | turn notebook code into a tested package, save models, serve them with FastAPI |
# | 10-11 | Shipping | work locally in VS Code, use Docker and CI, deploy, monitor and update a model |
# | 12 | Capstone | finish the project, present it, prepare for interviews |
#
# **A week** has three lessons (like this one) and one lab, about 6-8 hours in total. A **lesson** is a
# series of short sections. Each one follows the same rhythm:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c01-01.svg" alt="Each section: why, idea, see it, try it, exercise, grader" style="max-width:100%">
#
# A **lab** combines the week's lessons on one realistic task, step by step, and is graded the same way.
# From week 7 the labs become milestones of one project: detecting faults in an industrial water pump from
# its sensor data.

# %% [markdown]
# ## 2. Colab in ten minutes
#
# **Why.** Colab gives you a ready-made Python computer in the browser, with the libraries data scientists
# use already installed. You will spend most of this course in it.
#
# **The idea.** A notebook is a list of **cells**. A *text cell* (like this one) holds formatted text. A
# *code cell* holds Python. You run a code cell with **Shift+Enter** (run and move on) or the ▶ button on its
# left. The output appears under the cell.
#
# Behind the page sits a **runtime**: a temporary virtual machine in a Google data centre that actually runs
# your code. Your browser only displays the notebook.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c01-02.svg" alt="Your browser shows the notebook; a temporary runtime runs the code and holds files and variables; Drive and GitHub keep things permanently" style="max-width:100%">
#
# Three things to remember from the picture:
#
# 1. Variables live in the runtime's **memory**. They exist until the runtime restarts.
# 2. Files your code writes live on the runtime's **disk**, under `/content`. They disappear when the
#    runtime is recycled (after about 90 minutes idle, or 12 hours at most on the free tier).
# 3. Only **Google Drive** and **GitHub** keep things permanently.
#
# **See it.** Run the next cell. The last expression in a cell is displayed automatically; `print` shows
# anything you ask for.

# %%
import platform

course_weeks = 12
print("Python version:", platform.python_version())
f"This course has {course_weeks} weeks"

# %% [markdown]
# **Try it.** Change `course_weeks` to another number and run the cell again. Then add a new code cell below
# (hover between two cells and click **+ Code**), type `2 ** 10`, and run it.
#
# **Exercise 1.** Your first graded exercise. Complete the function so it returns the sum of its two
# arguments. Delete the two lines that say `# YOUR CODE HERE` and `raise NotImplementedError()` and write your
# own code instead. Then run the cell, and run the grader cell under it.

# %%
def add(a, b):
    """Return a + b."""
    ### BEGIN SOLUTION
    return a + b
    ### END SOLUTION

# %%
grade("w01.add", add)

# %% [markdown]
# What happened: `grade` called your `add` with several pairs of numbers, including negative and decimal
# ones, and compared the results with the expected values. If something is wrong, the message says which
# input failed. You can fix your code and re-run both cells as often as you like.
#
# **Exercise 2.** Format a number of minutes for a person to read: `75` becomes `"1 h 15 min"`, `120`
# becomes `"2 h"`, `45` becomes `"45 min"`, and `0` becomes `"0 min"`.
#
# Two Python tools help. `divmod(75, 60)` returns the pair `(1, 15)`: the whole hours and the minutes left over.
# An *f-string* builds text from values: `f"{h} h"` with `h = 1` gives `"1 h"`.

# %%
def minutes_to_text(minutes):
    """Turn a number of minutes into text such as '1 h 15 min', '2 h' or '45 min'."""
    ### BEGIN SOLUTION
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"
    return f"{mins} min"
    ### END SOLUTION

# %%
grade("w01.minutes_to_text", minutes_to_text)

# %% [markdown]
# ## 3. The notebook trap: run order
#
# **Why.** The most common notebook bug is not in any single cell. It comes from running cells out of order,
# so the notebook works on your screen and fails for everybody else, including you tomorrow.
#
# **The idea.** The runtime remembers what you *ran*, not what you *see*. The number in brackets left of a
# code cell, like `[7]`, is the order in which it ran. If you run cell C, then edit and re-run cell A, the
# page shows A above C, but C was computed with the *old* A.
#
# **See it.** Run the next three cells in order: first the one that sets the price, then the total, then
# change the price cell to `price = 20` and run **only** that cell.

# %%
price = 10

# %%
quantity = 3
total = price * quantity
total

# %%
print("price is now", price, "but total is still", total)

# %% [markdown]
# `total` is still 30, even though the page now says `price = 20`. Nothing recomputed it. In a long notebook
# this is how a chart ends up showing numbers that no cell on the screen produces.
#
# **The habit that prevents it:** before you trust a notebook, use **Runtime → Restart session and run all**.
# If it runs top to bottom without errors and gives the same answers, the notebook really works. Every
# notebook in this course is tested that way.
#
# **Try it.** Use **Runtime → Restart session**, then run only the last cell above. Read the error:
# `NameError: name 'price' is not defined`. After a restart memory is empty, so cells that define things must
# run first. (Run the setup cell again afterwards, then continue.)

# %% [markdown]
# ## 4. Files in Colab, and what survives a reset
#
# **Why.** Real work reads and writes files: data, models, reports. You need to know where they go and how long
# they last.
#
# **The idea.** The setup cell copied this course from GitHub into the folder `/content/mlengineering` on the
# runtime's disk and made it the **current folder**. Paths such as `data/course` are relative to it.
#
# Colab also lets you run **shell commands**: put `!` at the start of a line and Colab hands it to the
# machine's command line instead of Python. Week 1's third lesson teaches the command line properly; for now,
# `!ls` lists a folder and `!pwd` prints the current folder.
#
# **See it.**

# %%
!pwd
!ls
!ls -l data/course

# %% [markdown]
# The **Files** panel on the left (the folder icon) shows the same folders. You can open, download and
# upload files there.
#
# **Exercise 3.** The course keeps small practice databases in `data/course` (files ending in `.db`).
# Look at the listing above and set `n_databases` to how many there are.

# %%
### BEGIN SOLUTION
n_databases = len(list(Path("data/course").glob("*.db")))
### STARTER
n_databases = None  # YOUR ANSWER HERE: a whole number
### END SOLUTION

# %%
grade("w01.count_course_databases", n_databases)

# %% [markdown]
# **Writing files from Python.** The `pathlib` module (part of Python) treats paths as objects.
# `Path("notes") / "today.txt"` builds the path `notes/today.txt` on any operating system, and a path object
# can create folders, write and read text:
#
# ```python
# from pathlib import Path
# target = Path("my_notes") / "today.txt"
# target.parent.mkdir(parents=True, exist_ok=True)   # create the folder if it is missing
# target.write_text("Learned about runtimes.")
# print(target.read_text())
# ```
#
# **Exercise 4.** Write `save_note(text, path)`: make sure the folder of `path` exists, write `text` to the
# file, and return the path. The grader also gives you paths inside folders that do not exist yet.

# %%
def save_note(text, path):
    """Write text to path (creating missing folders) and return the path."""
    path = Path(path)
    ### BEGIN SOLUTION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
    ### END SOLUTION

# %%
grade("w01.save_note", save_note)

# %% [markdown]
# **Exercise 5.** A program that runs again after a reset should not crash because a file it saved earlier is
# gone. Write `load_or_default(path, default)`: return the file's text if the file exists, otherwise return
# `default`. (`Path(path).exists()` tells you whether a file is there.)

# %%
def load_or_default(path, default):
    """Return the text of the file at path, or default if there is no such file."""
    ### BEGIN SOLUTION
    path = Path(path)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return default
    ### END SOLUTION

# %%
grade("w01.load_or_default", load_or_default)

# %% [markdown]
# **Exercise 6.** The runtime resets. Which of these still exist afterwards, without you doing anything?
# Put the letters in a set, for example `{"a", "d"}`.
#
# - **a.** A variable `model` you trained in a cell.
# - **b.** A file `labs/my_answers.txt` you wrote inside `/content/mlengineering`.
# - **c.** This notebook's text, if you opened it from GitHub with the Colab badge and saved a copy to Drive.
# - **d.** A package you installed with `!pip install`.

# %%
### BEGIN SOLUTION
survivors = {"c"}
### STARTER
survivors = set()  # YOUR ANSWER HERE, e.g. {"a"}
### END SOLUTION

# %%
grade("w01.runtime_survivors", survivors)

# %% [markdown]
# ## 5. Saving your work
#
# Opening a notebook from the badge gives you a *read-only view* of the course version. To keep your answers:
#
# 1. **File → Save a copy in Drive.** Colab makes your own copy in *My Drive / Colab Notebooks* and opens it.
#    Work in that copy from now on; it saves itself as you type. This keeps the **notebook** (your code and
#    text), not the files the code wrote.
# 2. **Files your code wrote** (reports, models) live on the runtime's disk. To keep one, download it from the
#    Files panel, or connect Drive:
#
# ```python
# from google.colab import drive
# drive.mount("/content/drive")          # asks for permission once
# # then save under /content/drive/MyDrive/... instead of the course folder
# ```
#
# 3. **Labs that edit files** in later weeks say exactly what to save and how. From week 10 you can also work
#    on your own computer in VS Code, where nothing is wiped.
#
# When you come back the next day: open your Drive copy, then run the setup cell first. It downloads the
# course again into a fresh runtime.

# %% [markdown]
# ## 6. How grading and quizzes work
#
# You have already used `grade(...)`. Some rules of the game:
#
# - A grader runs your code on **several inputs**, including awkward ones (empty lists, zero, missing files).
#   Passing means your code handles those cases, which is exactly the habit the job needs.
# - Failure messages say *what* is wrong, never the solution. If you are stuck, re-read the section, use the
#   hint printed under the message, then look at the tool guide.
# - Solutions exist, in the course repository under `solutions/notebooks/`. Open one only after a real attempt.
#   Copying a solution teaches you to copy.
#
# **Exercise 7.** The course plan is stored as a file, `curriculum.json`, in the course folder. JSON is a text
# format for structured data: lists `[...]`, and dictionaries `{"key": value}`. Python's `json` module turns it
# into Python lists and dicts:
#
# ```python
# import json
# data = json.loads(Path("curriculum.json").read_text())
# data["notebooks"][0]       # {'notebook': '01_welcome_and_colab', 'week': 1, 'kind': 'lesson', ...}
# ```
#
# Write `notebooks_in_week(week)`: return the list of **titles** of the notebooks in that week, in course order.
# A week that does not exist gives an empty list.

# %%
import json

def notebooks_in_week(week):
    """Titles of the notebooks in the given week, in course order."""
    ### BEGIN SOLUTION
    data = json.loads(Path("curriculum.json").read_text())
    return [n["title"] for n in data["notebooks"] if n["week"] == week]
    ### END SOLUTION

# %%
grade("w01.notebooks_in_week", notebooks_in_week)

# %%
notebooks_in_week(1)

# %% [markdown]
# **Exercise 8.** Each entry in `curriculum.json` also has `"minutes"`. Write `course_hours(minutes)`: given a list
# of minutes, return the total in hours, rounded to one decimal place. Then use it to see how long the whole
# course is.

# %%
def course_hours(minutes):
    """Total of a list of minutes, in hours, rounded to 1 decimal."""
    ### BEGIN SOLUTION
    return round(sum(minutes) / 60, 1)
    ### END SOLUTION

# %%
grade("w01.course_hours", course_hours)

# %%
all_minutes = [n["minutes"] for n in json.loads(Path("curriculum.json").read_text())["notebooks"]]
print("Whole course:", course_hours(all_minutes), "hours of notebooks, plus reading and the project")

# %% [markdown]
# **Quizzes** check understanding. Put the letter of your answer between the quotes and run the cell; the
# reply explains why each answer is right or wrong.

# %% [markdown]
# ## Quiz
#
# **Q1.** You edited a cell near the top of a long notebook and re-ran only that cell. What do the cells below it show?
#
# - a. The new results: Colab re-runs cells that depend on the edited one.
# - b. The old results, computed before your edit, until you run them again.
# - c. Nothing: their outputs are cleared until you save.
# - d. It depends only on the order of cells on the page.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.01_q1", answer)

# %% [markdown]
# **Q2.** You trained a model, wrote it to `/content/model.pkl`, saved the notebook and closed the tab. The next
# day the runtime has been recycled. What is true?
#
# - a. The file is still there because you saved the notebook.
# - b. The file is there because saving the notebook saves its files.
# - c. The file is gone; only what you stored in Drive or GitHub (or downloaded) survives.
# - d. The file is in your browser's downloads folder.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.01_q2", answer)

# %% [markdown]
# **Q3.** What does a passing grader tell you?
#
# - a. Your code produced the expected results on the grader's inputs, including some awkward cases.
# - b. Your code is identical to the solution.
# - c. You may not run the grader again.
# - d. You have mastered the topic and can skip the lab.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.01_q3", answer)

# %% [markdown]
# **Q4.** What does `!` at the start of a line in a Colab code cell do?
#
# - a. It negates the Python expression that follows.
# - b. It turns the line into a comment.
# - c. It installs a package.
# - d. It runs the line as a command in the machine's shell (command line).

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.01_q4", answer)

# %% [markdown]
# ## Recap
#
# - A notebook is cells; a runtime (a temporary machine) runs them and holds variables and files.
# - The runtime remembers the order you ran cells, not the order on the page. **Restart and run all** before trusting results.
# - Files under `/content` vanish when the runtime is recycled; keep work in Drive (and, later, GitHub).
# - `!command` runs a shell command; `pathlib.Path` builds and uses file paths; `json` reads structured data.
# - Every exercise is followed by a grader; every lesson ends with a quiz.
#
# ## On the job
#
# Notebooks are where most ML work *starts*: exploring data, trying a model. The run-order trap is why teams
# move important code out of notebooks into files with tests (week 8), and why "it works on my machine" is
# not accepted as evidence. The habits from today (restart and run all, know where files live, save to a real
# store) are the first step.
#
# ## Going further
#
# - Tool guide: [Google Colab](../docs/tools/colab.md).
# - Next: [02 · Python for engineers](02_python_for_engineers.ipynb).

# %% [markdown]
# ## Record your progress
#
# Your progress is stored in `progress/progress.json` in the course folder. In Colab that folder is reset with
# the runtime, so also keep your own checklist; on your computer (week 10) it persists. Flags: `reading`,
# `guided` (you passed the graded exercises), `independent` (you solved them without hints or solutions),
# `review` (come back to this).

# %%
from mlcourse.progress import mark

# mark("01", "reading")
# mark("01", "guided")
