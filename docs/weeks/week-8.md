---
title: "Week 8 · Code you can trust"
parent: Weekly plan
nav_order: 8
---

# Week 8 · Code you can trust

**Goal:** turn notebook code into a tested, configurable Python package.

Until now your code has lived in notebooks. This week it moves into a **package** that can be installed, imported
and run as a terminal command; it gets a **test suite** that catches realistic bugs; and every run is driven by a
**config file**, writes a **log**, and leaves a **run folder** from which it can be reproduced. The lab packages the
churn model from Weeks 4-5 as `churnkit`. Everything runs in Google Colab: you write files with `%%writefile`,
install them with `%pip install -e`, and run `python -m pytest` from a cell.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 29 | From notebook to Python package | lesson | 100 min | [read](../notebooks/29_notebook_to_package.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/29_notebook_to_package.ipynb) |
| 30 | Testing with pytest | lesson | 100 min | [read](../notebooks/30_testing_with_pytest.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/30_testing_with_pytest.ipynb) |
| 31 | Configuration, logging and reproducibility | lesson | 90 min | [read](../notebooks/31_config_logging_reproducibility.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/31_config_logging_reproducibility.ipynb) |
| 32 | Lab: package and test the churn pipeline | lab | 100 min | [read](../notebooks/32_lab_package_and_test.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/32_lab_package_and_test.ipynb) |

## Before you start

* Week 1: functions, files and the terminal (notebooks 02-03). You will run commands like `cd` and `python -m ...`.
* Weeks 4-5: the churn table (cutoff, active customers, label window) and scikit-learn pipelines.
* No packaging, testing or logging experience is assumed.

## What you will be able to do

* refactor notebook cells into pure functions, modules and a package with the `src/` layout;
* write `pyproject.toml` line by line, install with `pip install -e`, and add a terminal command with argparse;
* write pytest tests with fixtures, parametrize and `tmp_path`; compare floats and DataFrames with tolerances; read
  a failure report;
* decide what to test in ML code (features, boundaries, splits, "fitted on train only") and what not to (accuracy);
* judge a test suite by whether it catches planted bugs (mutation testing);
* load settings from YAML into a dataclass, apply `key=value` overrides and validate them;
* log with levels, timestamps and a file; control randomness with seeds; save and re-run a run folder.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 29, sections 1-3 (pure functions, modules, the `__main__` guard, packages) | 1 h |
| 2 | Notebook 29, sections 4-5 and quiz (`pyproject.toml`, `pip install -e`, a command) | 45 min |
| 3 | Notebook 30, sections 1-3 (asserts, running pytest, reading failures, tolerances) | 1 h |
| 4 | Notebook 30, sections 4-5 and quiz (fixtures, parametrize, `tmp_path`, testing ML code) | 1 h |
| 5 | Notebook 31 (config files, overrides, logging, seeds, run folders) | 1.5 h |
| 6 | Notebook 32, the lab, without looking at the solutions | 1.5-2 h |
| 7 | Review: put `churnkit` in a Git repository with a README; skim both tool guides' cheat sheets | 30 min |

The working files of this week live in `/content/work` in Colab, which is deleted when the session ends. Each
notebook recreates what it needs, but download your `churnkit` folder (or copy it to Google Drive) when you finish
the lab: it is a portfolio piece.

## Tool guides

* [Python packaging and environments](../tools/packaging.html): how imports work, the src layout,
  `pyproject.toml`, virtual environments, commands, lock files, common install errors and a cheat sheet.
* [pytest](../tools/pytest.html): discovery, running and reading failures, fixtures, parametrize, comparing numbers
  and tables, what to test in ML code, common errors and a cheat sheet.

Next week: [Week 9 · Serving models](week-9.html).
