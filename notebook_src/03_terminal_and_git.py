# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/03_terminal_and_git.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 03 · The terminal and Git
#
# **Week 1 · lesson · about 100 minutes**
#
# Two tools sit under almost everything an ML engineer does: the **terminal** (typing commands instead of clicking)
# and **Git** (recording every version of your code). You will practise both right here in Colab, on files and a
# repository that live in a throwaway folder, so nothing you do can break anything.
#
# **What you will learn**
#
# - Move around and inspect files with `pwd`, `ls`, `cat`, `head`, `wc`, `grep`.
# - Combine small commands with pipes `|` and save output with `>` and `>>`.
# - Use Git: `init`, `status`, `add`, `commit`, `log`, `diff`, `.gitignore`, `branch`, `merge`, `restore`.
# - Understand what GitHub adds: remotes, `push` / `pull`, and pull requests.
#
# **What you need:** [01 · Welcome and Colab](01_welcome_and_colab.ipynb) (the `!` prefix).
#
# **How grading works:** graders inspect the files and the Git repository you create, so run the cells in order.

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
# ## 1. The terminal: commands instead of clicks
#
# **Why.** Servers, cloud machines and containers have no windows to click in. Logs are too big to open in an
# editor. Every tool you will meet in this course (Git, pytest, Docker, cloud tools) is driven by typed commands.
# Ten commands cover most days.
#
# **The idea.** A **terminal** (also *shell* or *command line*) runs one command per line: the program name, then
# **options** (start with `-`) and **arguments** (what to work on). `ls -l data` means "list, in long format, the
# folder `data`". Colab's machine runs Linux, whose shell is called **bash**; macOS uses the same commands, and on
# Windows you get them through *Git Bash* or *WSL* (see the [terminal guide](../docs/tools/terminal.md)).
#
# In a notebook, a line that starts with `!` is sent to the shell instead of Python. One catch: **every `!` line
# runs in a fresh shell**, so `!cd folder` on one line is forgotten on the next. Join commands with `&&`
# ("then, if that worked") on one line: `!cd folder && ls`.
#
# | Command | Does |
# |---|---|
# | `pwd` | print the folder you are in (*working directory*) |
# | `ls`, `ls -l` | list files (long format: size, date) |
# | `cd folder` | change folder; `..` means "one up" |
# | `mkdir -p a/b` | make folders (`-p`: parents too, no error if they exist) |
# | `cat`, `head -n 5`, `tail -n 5` | show a whole file, its first or last lines |
# | `wc -l` | count lines |
# | `grep text file` | show lines that contain `text` |
# | `rm file`, `rm -r folder` | delete (there is no recycle bin!) |
#
# **See it.** The next cell creates a practice web-server log: 240 lines, one per request, with the fields
# date, time, level, endpoint, HTTP status and response time. Then we look at it with the shell.

# %%
import random

practice = Path("/tmp/shell-practice")
subprocess.run(["rm", "-rf", str(practice)])     # start fresh every time
practice.mkdir(parents=True)
rng = random.Random(42)
endpoints = ["/api/orders"] * 5 + ["/api/products"] * 4 + ["/api/login"] * 3 + ["/api/cart"] * 3 + ["/health"] * 2
lines = []
for i in range(240):
    ep = rng.choice(endpoints)
    level = "ERROR" if rng.random() < 0.08 else ("WARN" if rng.random() < 0.1 else "INFO")
    status = 500 if level == "ERROR" else (429 if level == "WARN" else 200)
    ms = rng.randint(5, 900 if level != "INFO" else 300)
    h, m, s = 9 + i * 37 // 3600, i * 37 % 3600 // 60, i * 37 % 60
    lines.append(f"2026-03-02 {h:02d}:{m:02d}:{s:02d} {level} {ep} {status} {ms}ms")
(practice / "server.log").write_text("\n".join(lines) + "\n")
print("wrote", practice / "server.log")

# %%
!pwd
!ls -l /tmp/shell-practice
!head -n 3 /tmp/shell-practice/server.log
!grep "/health" /tmp/shell-practice/server.log | head -n 2

# %% [markdown]
# You should see the course folder from `pwd`, one file of about 11 KB from `ls -l`, and three log lines such as
# `2026-03-02 09:00:00 ERROR /api/orders 500 286ms`.
#
# **Try it.** Run `!tail -n 3 /tmp/shell-practice/server.log`, then `!ls --help | head -n 20`. Almost every command
# explains itself with `--help` (or `man ls` on your own computer).
#
# **Exercise 1.** How many lines does `server.log` have? Find out with `wc -l` and type the number.

# %%
### BEGIN SOLUTION
!wc -l /tmp/shell-practice/server.log
line_count = 240
### STARTER
# !wc -l /tmp/shell-practice/server.log
line_count = None  # YOUR ANSWER HERE: a whole number
### END SOLUTION

# %%
grade("w01.line_count", line_count)

# %% [markdown]
# **Exercise 2.** How many lines contain `ERROR`? `grep -c` counts matching lines instead of printing them.

# %%
### BEGIN SOLUTION
!grep -c ERROR /tmp/shell-practice/server.log
error_count = 13
### STARTER
# run a grep command here, then type the number below
error_count = None  # YOUR ANSWER HERE: a whole number
### END SOLUTION

# %%
grade("w01.error_count", error_count)

# %% [markdown]
# ## 2. Pipes and redirection
#
# **Why.** "Which endpoint gets the most traffic?" "Which errors happened after 11:00?" You can answer questions like
# these on a 5 GB log on a remote server in one line, without loading it into Python.
#
# **The idea.** Each command reads **input** and writes **output**. Three symbols connect them:
#
# | Symbol | Meaning | Example |
# |---|---|---|
# | `a \| b` | **pipe**: the output of `a` becomes the input of `b` | `grep ERROR log \| wc -l` |
# | `> file` | write output to a file (replaces it) | `grep ERROR log > errors.txt` |
# | `>> file` | append output to the end of a file | `echo "done" >> notes.txt` |
#
# Four more small tools make pipes powerful:
#
# - `cut -d " " -f 4` keeps field 4 of each line, where fields are separated by a space (`-d` = delimiter).
# - `sort` sorts lines; `sort -rn` sorts numerically (`-n`), largest first (`-r`).
# - `uniq -c` collapses *adjacent* repeated lines and counts them, which is why it almost always follows `sort`.
# - `echo text` prints its argument, handy with `>` to write a file.
#
# **See it.** The levels in the log, counted:

# %%
!cut -d " " -f 3 /tmp/shell-practice/server.log | sort | uniq -c

# %% [markdown]
# Read it left to right: take field 3 (the level), sort so equal levels are adjacent, count each run. The counts add up
# to 240.
#
# **Try it.** Build the pipeline one step at a time: run `cut ... | head`, then add `| sort | head`, then `| uniq -c`.
# Seeing each stage is how professionals debug a pipeline.
#
# **Exercise 3.** Which endpoint (field 4) appears most often? Build a pipeline ending in `sort -rn | head -n 1`, then
# type the endpoint as a string, such as `"/api/example"`.

# %%
### BEGIN SOLUTION
!cut -d " " -f 4 /tmp/shell-practice/server.log | sort | uniq -c | sort -rn | head -n 1
busiest = "/api/orders"
### STARTER
# YOUR PIPELINE HERE (a line starting with !)
busiest = None  # YOUR ANSWER HERE: a string
### END SOLUTION

# %%
grade("w01.busiest_endpoint", busiest)

# %% [markdown]
# **Exercise 4.** With `echo` and the two redirection symbols, create `/tmp/shell-practice/notes.txt` containing exactly
# two lines: `first line` and `second line`. Then check it with `cat`. (If you get it wrong, simply run your cell again:
# `>` starts the file over.)

# %%
### BEGIN SOLUTION
!echo "first line" > /tmp/shell-practice/notes.txt
!echo "second line" >> /tmp/shell-practice/notes.txt
!cat /tmp/shell-practice/notes.txt
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %%
grade("w01.shell_file", "/tmp/shell-practice/notes.txt")

# %% [markdown]
# ## 3. Git: saving versions of your work
#
# **Why.** Without version control, projects end up as `model_final_v2_REALLY_final.py`, nobody knows which version
# produced last month's results, and a bad edit cannot be undone. **Git** records every saved version of a project,
# with who changed what and why, and lets several people work on the same code safely. Every software team uses it.
#
# **The idea.** A **repository** (*repo*) is a folder whose history Git tracks; the history lives in a hidden `.git`
# folder inside it. Saving a version is two steps:
#
# 1. `git add file` puts the change in the **staging area**: "this goes into the next snapshot".
# 2. `git commit -m "message"` records a **commit**: a snapshot of the staged files, your message, the author and time,
#    and a link to the previous commit.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c03-01.svg" alt="working folder to staging area with git add, to local repository with git commit, to GitHub with git push; git pull brings changes back" style="max-width:100%">
#
# `git status` tells you, at any moment, which files are changed, staged or untracked. When in doubt, run it.
#
# Git needs to know your name and email to sign commits. In this practice repo we set them only for this repo
# (`git config user.name ...` without `--global`), with placeholder values.
#
# **See it.** We create an empty practice folder. You then turn it into a repository.

# %%
!rm -rf /tmp/git-practice
!mkdir -p /tmp/git-practice
!cd /tmp/git-practice && ls -a

# %% [markdown]
# The commands for your first commit, explained:
#
# ```bash
# cd /tmp/git-practice && git init -b main      # make this folder a repo; call the main branch "main"
# cd /tmp/git-practice && git config user.name "Course Student"
# cd /tmp/git-practice && git config user.email "student@example.com"
# echo "# Practice project" > /tmp/git-practice/README.md
# cd /tmp/git-practice && git status            # README.md is "untracked"
# cd /tmp/git-practice && git add README.md
# cd /tmp/git-practice && git commit -m "Add README"
# cd /tmp/git-practice && git log --oneline     # one line per commit: short id and message
# ```
#
# **Exercise 5.** Run these commands (each with `!` in front) to make your first commit. Read the output of
# `git status` before and after `git add`.

# %%
### BEGIN SOLUTION
!cd /tmp/git-practice && git init -b main
!cd /tmp/git-practice && git config user.name "Course Student"
!cd /tmp/git-practice && git config user.email "student@example.com"
!echo "# Practice project" > /tmp/git-practice/README.md
!cd /tmp/git-practice && git status
!cd /tmp/git-practice && git add README.md
!cd /tmp/git-practice && git commit -m "Add README"
!cd /tmp/git-practice && git log --oneline
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %%
grade("w01.first_commit", "/tmp/git-practice")

# %% [markdown]
# **See what changed before committing.** `git diff` shows lines added (`+`) and removed (`-`) since the last commit.
# It is the habit that stops you from committing a debugging `print` or a password by accident.

# %%
!echo "Run: python main.py" >> /tmp/git-practice/README.md
!cd /tmp/git-practice && git diff

# %% [markdown]
# **Exercise 6.** Make the history at least **three** commits long. Commit the README change above, then create
# another small file (for example `notes.txt` with `echo`) and commit it. Rules a reviewer would apply: every message
# says what changed (at least 5 characters, like `Add usage line to README`), and nothing is left uncommitted.
# `git status` should end with *nothing to commit, working tree clean*.

# %%
### BEGIN SOLUTION
!cd /tmp/git-practice && git add README.md && git commit -m "Add usage line to README"
!echo "Ideas for the project" > /tmp/git-practice/notes.txt
!cd /tmp/git-practice && git add notes.txt && git commit -m "Add notes file"
!cd /tmp/git-practice && git status
!cd /tmp/git-practice && git log --oneline
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %%
grade("w01.three_commits", "/tmp/git-practice")

# %% [markdown]
# ## 4. What not to commit: `.gitignore`
#
# **Why.** Datasets are large, `.env` files hold passwords and API keys, and model files and reports can be
# regenerated. Put them in Git and the repository becomes huge, or your secret becomes public the moment you push.
# A secret in Git history stays there even if you delete the file later.
#
# **The idea.** A file named `.gitignore` lists patterns Git should ignore: `data/` (a whole folder), `*.log` (all
# files ending in `.log`), `.env` (one file). Ignored files never show up in `git status` and `git add .` skips them.
# The `.gitignore` file itself *is* committed, so everyone on the team ignores the same things.
#
# **See it.** A big data file appears in the project:

# %%
!mkdir -p /tmp/git-practice/data
!seq 1 100000 > /tmp/git-practice/data/big.csv
!ls -l /tmp/git-practice/data
!cd /tmp/git-practice && git status --short

# %% [markdown]
# `git status --short` prints one line per file; `??` means *untracked*. Git offers to track `data/`. We do not want it.
#
# **Exercise 7.** Create `.gitignore` containing the line `data/`, commit it, and check that `git status --short`
# is now empty. `git check-ignore -v data/big.csv` tells you which rule ignores a file.

# %%
### BEGIN SOLUTION
!echo "data/" > /tmp/git-practice/.gitignore
!cd /tmp/git-practice && git add .gitignore && git commit -m "Ignore the data folder"
!cd /tmp/git-practice && git status --short
!cd /tmp/git-practice && git check-ignore -v data/big.csv
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %%
grade("w01.gitignore", "/tmp/git-practice")

# %% [markdown]
# ## 5. Branches, merging and undoing mistakes
#
# **Why.** You want to try an idea without risking the version that works. Several teammates work at once.
# **Branches** give each line of work its own space; **merging** brings finished work back.
#
# **The idea.** A branch is a movable label pointing at a commit. `main` is the usual name for the trusted line.
#
# ```bash
# git switch -c feature     # create branch "feature" and move to it (-c = create)
# # ... edit, add, commit: these commits move "feature" forward, "main" stays put
# git switch main           # go back; the files on disk change to main's version
# git merge feature         # bring feature's commits into main
# git branch                # list branches; * marks the current one
# ```
#
# If `main` has not moved since the branch started, Git simply moves the `main` label forward: a **fast-forward**
# merge. If both moved, Git creates a *merge commit* that joins the two lines (and asks for help if both changed the
# same lines: a *merge conflict*, covered in the [Git guide](../docs/tools/git-github.md)).
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c03-02.svg" alt="commits 1 to 3 on main, commit 4 on feature; after the merge main points to commit 4" style="max-width:100%">
#
# **Exercise 8.** Create a branch `feature`, add a file `feature.txt` there and commit it, switch back to `main`, and
# merge `feature`. Finish on `main`. Check with `git log --oneline --all` and `ls`.

# %%
### BEGIN SOLUTION
!cd /tmp/git-practice && git switch -c feature
!echo "A new feature" > /tmp/git-practice/feature.txt
!cd /tmp/git-practice && git add feature.txt && git commit -m "Add feature file"
!cd /tmp/git-practice && git switch main
!cd /tmp/git-practice && git merge feature
!cd /tmp/git-practice && git log --oneline --all
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %%
grade("w01.feature_branch", "/tmp/git-practice")

# %% [markdown]
# **Undoing a mistake.** The next cell "accidentally" deletes `README.md`. Because it was committed, Git can bring it
# back: `git restore README.md` replaces the file on disk with the last committed version. (It also throws away
# uncommitted edits to that file, so use it deliberately.)

# %%
!rm -f /tmp/git-practice/README.md
!cd /tmp/git-practice && git status --short

# %% [markdown]
# ` D README.md` means *deleted in the working folder*.
#
# **Exercise 9.** Restore `README.md` with Git and check with `cat` that its two lines are back.

# %%
### BEGIN SOLUTION
!cd /tmp/git-practice && git restore README.md
!cat /tmp/git-practice/README.md
### STARTER
# YOUR COMMANDS HERE
### END SOLUTION

# %%
grade("w01.restore_file", "/tmp/git-practice")

# %% [markdown]
# ## 6. GitHub: sharing and reviewing
#
# **Why.** Your repository so far lives on one machine (here, a Colab runtime that will be deleted). Teams need a
# shared copy, a backup, and a place to discuss changes before they reach `main`.
#
# **The idea.** **GitHub** is a website that hosts Git repositories (GitLab and Bitbucket are similar). Git is the
# tool; GitHub is a place to keep and review repositories.
#
# - A **remote** is a named link from your repo to a copy elsewhere, by convention called `origin`.
#   `git clone URL` downloads a repository and sets `origin` for you; the setup cell of every notebook clones this
#   course exactly that way.
# - `git push` uploads your new commits to the remote; `git pull` downloads commits others pushed.
# - A **pull request** (PR) is a GitHub page that says "please review my branch and merge it into `main`".
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c03-03.svg" alt="commit on a branch, push it, open a pull request, review with comments and checks, merge into main" style="max-width:100%">
#
# **What you would see on GitHub.** A repository page shows the file list with the README rendered below it; above
# the files, a branch selector (it says `main`) and a green **Code** button that gives the URL to clone. After you push
# a branch, a yellow banner offers **Compare & pull request**. The pull request page has a title and description at
# the top, then tabs: **Conversation** (comments and approvals), **Commits**, **Checks** (automated tests, week 10)
# and **Files changed**, a side-by-side diff where reviewers click a line to comment. At the bottom, a green
# **Merge pull request** button becomes active once the review is approved.
#
# We do **not** push from Colab: it would need your GitHub password or token typed into a notebook, which is exactly
# how credentials leak. Pushing from your own computer is explained step by step in the
# [Git and GitHub guide](../docs/tools/git-github.md); you will need it from week 10.
#
# **Try it.** Run `!cd /content/mlengineering && git remote -v` in Colab (or in your course folder on your computer).
# It shows the `origin` remote the setup cell created, pointing at the course repository on GitHub.

# %% [markdown]
# ## Quiz

# %% [markdown]
# **Q1.** You run `git add model.py`. What happened?
#
# - a. The change is recorded in the project's history.
# - b. The change is put in the staging area, ready to be included in the next commit.
# - c. The file is uploaded to GitHub.
# - d. A new branch called `model.py` is created.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.03_q1", answer)

# %% [markdown]
# **Q2.** Which description of a commit is accurate?
#
# - a. A copy of your project that is uploaded to GitHub immediately.
# - b. A list of only the lines you changed, without the rest of the project.
# - c. A draft you keep editing until it is final.
# - d. A snapshot of the tracked files plus a message, an author, a time, and a link to the previous commit.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.03_q2", answer)

# %% [markdown]
# **Q3.** Which files belong in `.gitignore`?
#
# - a. `train.py`, the training script.
# - b. `requirements.txt`, the list of packages.
# - c. `data/raw.csv`, `.env` (holds an API key) and the `outputs/` folder.
# - d. `README.md`.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.03_q3", answer)

# %% [markdown]
# **Q4.** What is a pull request?
#
# - a. A request, on GitHub, for teammates to review a branch before it is merged into `main`.
# - b. The `git pull` command downloading new commits.
# - c. A request to delete a branch.
# - d. A command built into Git that merges two branches.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.03_q4", answer)

# %% [markdown]
# **Q5.** What does `|` do in `grep ERROR server.log | wc -l`?
#
# - a. Writes the output of `grep` to a file called `wc`.
# - b. Sends the output of `grep` as the input of `wc -l`, which counts its lines.
# - c. Runs both commands at the same time to make them faster.
# - d. Starts a comment; `wc -l` is ignored.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w01.03_q5", answer)

# %% [markdown]
# ## Recap
#
# - The shell runs `command -options arguments`; in a notebook, `!` sends a line to it, and every `!` line starts fresh.
# - `ls`, `cat`, `head`, `wc -l`, `grep` inspect files; `|` chains commands, `>` and `>>` write files.
# - `cut | sort | uniq -c | sort -rn` answers "what is most common?" on files of any size.
# - Git saves versions in two steps: `git add` (stage), `git commit -m` (snapshot with a message).
# - `git status`, `git diff` and `git log --oneline` tell you where you are; `git restore` brings back a committed file.
# - `.gitignore` keeps data, secrets and outputs out of the repository.
# - Branches isolate work; `git merge` brings it back; GitHub adds a shared remote and pull requests for review.
#
# ## On the job
#
# An ML engineer's day starts with `git pull`, ends with a pushed branch and a pull request, and in between runs
# commands on remote machines: `tail -f` on a service log, `grep` for a failing request ID, `ls -l` on a model
# folder. In week 10 the tests you write in week 8 will run automatically on every pull request.
#
# ## Going further
#
# - Tool guides: [The terminal](../docs/tools/terminal.md) and [Git and GitHub](../docs/tools/git-github.md).
# - Next: [04 · Lab: a small, tested data utility](04_lab_data_utility.ipynb).

# %%
from mlcourse.progress import mark

# mark("03", "reading")
# mark("03", "guided")
