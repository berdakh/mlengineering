---
title: "Week 1 · Your engineering workbench"
parent: Weekly plan
nav_order: 1
---

# Week 1 · Your engineering workbench

**Goal:** set up the tools you will use for the next eleven weeks, and write your first small, validated,
version-controlled piece of Python.

You learn how the course works and how to run, save and grade notebooks in Google Colab; you write Python the way
engineers do (functions with contracts, explicit errors, files); you practise the terminal and Git hands-on inside
Colab; and you finish with a lab that builds a CSV validator and commits it to a Git repository. Everything runs in
the browser; nothing needs installing.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 01 | Welcome, Colab, and how this course works | lesson | 75 min | [read](../notebooks/01_welcome_and_colab.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/01_welcome_and_colab.ipynb) |
| 02 | Python for engineers: functions, errors, files | lesson | 100 min | [read](../notebooks/02_python_for_engineers.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/02_python_for_engineers.ipynb) |
| 03 | The terminal and Git | lesson | 100 min | [read](../notebooks/03_terminal_and_git.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/03_terminal_and_git.ipynb) |
| 04 | Lab: a small, tested data utility | lab | 90 min | [read](../notebooks/04_lab_data_utility.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/04_lab_data_utility.ipynb) |

## Before you start

* A Google account (for Colab and for saving copies of notebooks to Google Drive).
* Basic Python: variables, `if`, `for`, lists, dictionaries, writing a simple function.
* No terminal, Git or software-engineering experience is assumed.

## What you will be able to do

* explain how the twelve weeks fit together, how graded exercises and quizzes work, and how to record progress;
* run, save and re-run notebooks in Colab, and explain why runtime files and variables disappear after a reset;
* write functions with type hints and docstrings that refuse bad input with specific exceptions;
* count, group and rank with dictionaries, comprehensions and `sorted`, and read and write text, JSON and CSV files;
* inspect files with `ls`, `head`, `wc`, `grep`, and combine commands with pipes and redirection;
* use Git to commit, inspect history and diffs, ignore files, branch and merge, and restore a file; explain push,
  pull and pull requests on GitHub;
* build a small data-validation module, step by step, and put it under version control.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 01: the course, Colab, saving your work, first graded exercises | 1.25 h |
| 2 | Notebook 02, sections 1-2 (functions, exceptions) | 45 min |
| 3 | Notebook 02, sections 3-4 and quiz (dictionaries, sorting, files) | 1 h |
| 4 | Notebook 03, sections 1-2 (terminal, pipes, redirection) | 45 min |
| 5 | Notebook 03, sections 3-6 and quiz (Git, `.gitignore`, branches, GitHub) | 1 h |
| 6 | Notebook 04, the lab, without looking at the solutions | 1.5 h |
| 7 | Review: skim the four tool guides' cheat sheets; redo any exercise you needed a hint for | 30 min |

If a session runs long, stop at the end of a section. Save a copy of each notebook to Drive first
(*File → Save a copy in Drive*), and after a break run the setup cell and *Runtime → Run all* to get back to where
you were.

## Tool guides

* [Google Colab](../tools/colab.html): opening, saving, running, magics, common errors, running locally.
* [Python for engineers](../tools/python-for-engineers.html): functions, exceptions, data structures, files.
* [The terminal (bash)](../tools/terminal.html): commands, pipes, redirection, Windows and macOS notes.
* [Git and GitHub](../tools/git-github.html): the everyday Git loop, branches, undoing, pushing, pull requests.

Next week: [Week 2 · SQL from zero](week-2.html).
