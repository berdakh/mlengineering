# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/29_notebook_to_package.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 29 · From notebook to Python package
#
# **Week 8 · lesson · about 100 minutes**
#
# Until now, all your code has lived in notebooks. That is the right place to explore, but it is a poor place to
# *keep* code: a function you wrote in notebook 14 is not available in notebook 20 unless you copy it, and copies
# drift apart. This week turns notebook code into code a team can trust. Today: the **package**, the standard way
# Python code is shared, installed and imported.
#
# **What you will learn**
#
# - Turn notebook cells into **pure functions**: inputs in, result out, no hidden state.
# - Put functions in a **module** (a `.py` file), import it, and understand why Python sometimes keeps an old version.
# - Organise modules into a **package** with the `src/` layout and an `__init__.py`.
# - Describe the package in `pyproject.toml`, line by line, and install it with `pip install -e`.
# - Add a **command-line entry point**, so your code runs as a terminal command.
#
# **What you need:** notebooks 02 (functions, files) and 03 (the terminal), and the churn data from Week 4.
#
# **How grading works:** most exercises this week are *files* you write with `%%writefile`. The grader imports your
# file freshly from disk each time and checks how it behaves on several inputs.

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
# ### Your working folder
#
# This week you create real files and folders. They go in a **working folder**: `/content/work` in Colab, or a
# `work/` folder inside the course on your own computer. `work_dir()` creates it and tells you where it is.
# `show_tree(folder)` prints a folder as a tree, and `load_module(...)` imports a module freshly (section 2 explains
# why you need it).
#
# In Colab, files in `/content` disappear when the session ends. That is fine for this lesson: every cell recreates
# what it needs. To keep your work, download the folder (Files panel on the left, right-click, Download) or copy it to
# Google Drive.

# %%
import pandas as pd
from mlcourse.sql import sql
from mlcourse.graders.w08 import work_dir, show_tree, load_module

WORK = work_dir()
PROJECT = WORK / "shopfeat"            # the package you build in this notebook
(WORK / "data").mkdir(exist_ok=True)

# Two CSV files from the shop database, used by the command-line tool at the end of the notebook.
orders = sql("SELECT * FROM orders", "shop")
orders["order_date"] = pd.to_datetime(orders["order_date"])
items = sql("SELECT * FROM order_items", "shop")
orders.to_csv(WORK / "data" / "orders.csv", index=False)
items.to_csv(WORK / "data" / "order_items.csv", index=False)
print("working folder:", WORK)
print(len(orders), "orders and", len(items), "order lines saved as CSV")

# %% [markdown]
# ## 1. From cells to pure functions
#
# **Why.** Imagine three notebooks that each compute "order value". One gets fixed after someone notices discounts
# were ignored; the other two are not. Next month two dashboards disagree and nobody knows which number is right.
# This is the **copy-paste problem**, and it is one of the most common sources of bugs in data teams.
#
# **Idea.** The cure has four steps, and this notebook walks through all of them:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c29-01.svg" alt="Notebook cells become functions, functions go into a module, modules into a package, and the package is installed and imported everywhere" style="max-width:100%">
#
# The first step is a **pure function**: it gets everything it needs from its arguments and gives back its result.
# It does not read global variables, does not change its inputs, and does not print. Pure functions are easy to move,
# easy to reuse and easy to test, because the same inputs always give the same output.
#
# **See it.** Here is typical notebook code. It works, but it depends on the variables `items` and `orders` that
# happen to exist, it changes `items` by adding a column, and the cutoff is buried in the middle.

# %%
# Typical notebook code: works once, hard to reuse.
items_nb = items.copy()
items_nb["line_value"] = items_nb["quantity"] * items_nb["unit_price"] * (1 - items_nb["discount"])
value_per_order = items_nb.groupby("order_id")["line_value"].sum()
print(value_per_order.head(3))

# %% [markdown]
# The same logic as a pure function: the input is an argument, nothing outside changes, the result is returned.

# %%
def line_values(items):
    """Value of each order line: quantity × unit_price × (1 − discount)."""
    return items["quantity"] * items["unit_price"] * (1 - items["discount"])


print(line_values(items).head(3))
print("columns of items are unchanged:", list(items.columns))

# %% [markdown]
# **Try it.** Call `line_values` on only the first two rows (`items.head(2)`). Before you run it, predict: does the
# result have two values or as many as `items`?

# %%
line_values(items.head(2))

# %% [markdown]
# ### Exercise 1 · `order_values`
#
# Write `order_values(items)`: return a pandas **Series** with one value per `order_id` (the index), equal to the sum
# of quantity × unit_price × (1 − discount) over that order's lines. Do not modify `items`. An empty table should
# give an empty Series.

# %%
def order_values(items):
    ### BEGIN SOLUTION
    line = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    return line.groupby(items["order_id"]).sum()
    ### END SOLUTION


# %%
grade("w08.order_values", order_values)

# %% [markdown]
# ### Exercise 2 · `days_since_last_order`
#
# Write `days_since_last_order(orders, cutoff)`: a Series indexed by `customer_id`, with the number of whole days
# from each customer's **last non-cancelled order on or before the cutoff** to the cutoff. Customers with no such
# order do not appear. `cutoff` may be a string such as `"2025-06-30"`, so convert it with `pd.Timestamp(cutoff)`.
# Use `.dt.days` to turn time differences into whole numbers of days.

# %%
def days_since_last_order(orders, cutoff):
    ### BEGIN SOLUTION
    cutoff = pd.Timestamp(cutoff)
    past = orders[(orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)]
    return (cutoff - past.groupby("customer_id")["order_date"].max()).dt.days
    ### END SOLUTION


# %%
grade("w08.days_since_last_order", days_since_last_order)

# %% [markdown]
# ## 2. Modules: code in a `.py` file
#
# **Why.** A function in a notebook dies with the notebook. A function in a file can be imported by any notebook,
# script, test or web service.
#
# **Idea.** A **module** is simply a `.py` file. `import greetings` makes Python look for `greetings.py` in each
# folder of a list called `sys.path` (the current folder, the installed packages, and anything you add), run the
# file once, and give you its functions as `greetings.something`.
#
# Two consequences matter in practice:
#
# 1. **Importing runs the file.** Every top-level line runs at import. A module should only *define* things
#    (functions, constants); it should not print, read big files or train models when imported.
# 2. **Python imports a module only once per session.** It keeps it in a cache (`sys.modules`). If you edit the file
#    and `import` it again, you still get the *old* version. In a notebook you either restart the kernel
#    (Runtime → Restart session), call `importlib.reload(module)`, or use the course helper `load_module`, which forgets
#    the cache and reads the file again.
#
# **See it.** `%%writefile path` at the top of a cell writes the rest of the cell to a file instead of running it.
# The `{WORK}` part is replaced by the value of the Python variable `WORK`.

# %%
# %%writefile only writes into existing folders, so create the folder first.
(WORK / "demo").mkdir(exist_ok=True)
sys.path.insert(0, str(WORK / "demo"))   # let Python find modules in this folder
print(sys.path[0])

# %%
%%writefile {WORK}/demo/greetings.py
"""A tiny module."""

GREETING = "Hello"


def greet(name):
    return f"{GREETING}, {name}!"

# %%
import greetings
print(greetings.greet("Aru"))

# %% [markdown]
# **Try it.** Edit the cell that writes `greetings.py`: change `"Hello"` to `"Salem"`, run it, then run the cell
# above again. You still see "Hello": Python used its cached copy. Now run the next cell, which reloads.

# %%
import importlib
importlib.reload(greetings)
print(greetings.greet("Aru"))

# %% [markdown]
# ### Exercise 3 · the features module
#
# Your package will be called `shopfeat` (shop features). Write its first module, `src/shopfeat/features.py`, with
# your two functions from Exercises 1 and 2. Put `import pandas as pd` at the top, because a module only sees what
# it imports itself, not the notebook's variables. The grader checks that importing the file prints nothing, then
# tests both functions.
#
# (You will see why the folder is called `src/shopfeat` in section 3.)

# %%
(PROJECT / "src" / "shopfeat").mkdir(parents=True, exist_ok=True)

# %%
%%writefile {PROJECT}/src/shopfeat/features.py
"""Feature functions for the shop data."""
import pandas as pd


def order_values(items):
    """Value of each order: sum of quantity * unit_price * (1 - discount), indexed by order_id."""
    ### BEGIN SOLUTION
    line = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    return line.groupby(items["order_id"]).sum()
    ### END SOLUTION


def days_since_last_order(orders, cutoff):
    """Whole days from each customer's last non-cancelled order on or before cutoff, to the cutoff."""
    ### BEGIN SOLUTION
    cutoff = pd.Timestamp(cutoff)
    past = orders[(orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)]
    return (cutoff - past.groupby("customer_id")["order_date"].max()).dt.days
    ### END SOLUTION

# %%
grade("w08.features_module", PROJECT)

# %% [markdown]
# ### The `__main__` guard
#
# Sometimes one file is both a module (other code imports its functions) and a script (you run it with
# `python file.py`). Python sets a special variable `__name__` in every file: it is `"__main__"` when the file is run
# directly, and the module's name when it is imported. So code under
#
# ```python
# if __name__ == "__main__":
#     ...
# ```
#
# runs on `python file.py` but **not** on `import`. The next cell writes a script that prints a report as soon as it
# is imported, which is exactly what you do not want.

# %%
%%writefile {WORK}/demo/monthly_report.py
import pandas as pd

orders = pd.DataFrame({"customer_id": [1, 1, 2], "value": [10.0, 5.5, 7.0]})
total = orders["value"].sum()
print(f"Report: {len(orders)} orders, total {total:.2f}")

# %%
import monthly_report        # importing it prints the report: a side effect

# %% [markdown]
# ### Exercise 4 · a module that is also a script
#
# Rewrite the script as `monthly_report_v2.py`:
#
# - a function `make_report(orders)` that **returns** the text `"Report: N orders, total T"` (T with two decimals),
#   for any DataFrame with a `value` column;
# - the demo table and the `print` moved under `if __name__ == "__main__":`.
#
# Importing it must print nothing; `python monthly_report_v2.py` must still print `Report: 3 orders, total 22.50`.

# %%
%%writefile {WORK}/demo/monthly_report_v2.py
### BEGIN SOLUTION
import pandas as pd


def make_report(orders):
    return f"Report: {len(orders)} orders, total {orders['value'].sum():.2f}"


if __name__ == "__main__":
    demo = pd.DataFrame({"customer_id": [1, 1, 2], "value": [10.0, 5.5, 7.0]})
    print(make_report(demo))
### STARTER
# YOUR CODE HERE: make_report(orders), then the demo under the __main__ guard
raise NotImplementedError()
### END SOLUTION

# %%
!python "{WORK}/demo/monthly_report_v2.py"

# %%
grade("w08.main_guard", WORK / "demo" / "monthly_report_v2.py")

# %% [markdown]
# ## 3. Packages and the `src/` layout
#
# **Why.** One file is fine for twenty lines. Real projects have features, models, reports and command-line tools;
# they need a folder structure that every Python tool understands.
#
# **Idea.** A **package** is a folder of modules with an `__init__.py` file in it. `import shopfeat` runs
# `shopfeat/__init__.py`; `import shopfeat.features` runs `shopfeat/features.py`. Most teams use the **`src/` layout**:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c29-02.svg" alt="The shopfeat project: pyproject.toml and tests at the top, the package shopfeat inside src with __init__.py, features.py, report.py and cli.py" style="max-width:100%">
#
# - The **project folder** (`shopfeat/`) holds everything: the package, its tests, its description `pyproject.toml`.
# - The **package** lives one level down, in `src/shopfeat/`. Putting it under `src/` means you cannot accidentally
#   import it just because you are standing in the project folder; you must *install* it, so you always test what
#   users will get.
# - `__init__.py` usually holds the version number and **re-exports** the most useful functions, so users can write
#   `shopfeat.order_values` instead of `shopfeat.features.order_values`.
#
# Inside a package, modules import each other with **relative imports**: in `report.py`,
# `from .features import order_values` means "from the module `features` in *this* package". The dot is the package.
#
# **See it.** A complete demo package, `tinytools`, with one module.

# %%
DEMO = WORK / "tinytools"
(DEMO / "src" / "tinytools").mkdir(parents=True, exist_ok=True)

# %%
%%writefile {DEMO}/src/tinytools/textstats.py
"""Simple statistics about text."""


def word_count(text):
    return len(text.split())

# %%
%%writefile {DEMO}/src/tinytools/__init__.py
"""tinytools: a demo package."""
__version__ = "0.1.0"

from .textstats import word_count

# %%
show_tree(DEMO)
tinytools = load_module(DEMO, "tinytools")       # import freshly from DEMO/src
print("version", tinytools.__version__, "| word_count:", tinytools.word_count("one two three"))

# %% [markdown]
# **Try it.** Add a second function `char_count(text)` to `textstats.py`, re-export it in `__init__.py`, and call
# `load_module(DEMO, "tinytools").char_count("abc")`.

# %%
# your experiment here

# %% [markdown]
# ### Exercise 5 · `__init__.py` for shopfeat
#
# Write `src/shopfeat/__init__.py`: a one-line docstring, `__version__ = "0.1.0"`, and a relative import that
# re-exports `order_values` and `days_since_last_order` from the features module.

# %%
%%writefile {PROJECT}/src/shopfeat/__init__.py
"""shopfeat: features and reports for the shop data."""
### BEGIN SOLUTION
__version__ = "0.1.0"

from .features import days_since_last_order, order_values
### STARTER
__version__ = None  # YOUR CODE HERE (and the re-export)
### END SOLUTION

# %%
grade("w08.package_init", PROJECT)

# %% [markdown]
# ### Exercise 6 · a second module that reuses the first
#
# Write `src/shopfeat/report.py` with `customer_summary(orders, items, cutoff)`. It returns a DataFrame indexed by
# `customer_id`, one row per customer with at least one non-cancelled order on or before the cutoff, with columns:
#
# | column | meaning |
# |---|---|
# | `n_orders` | number of non-cancelled orders on or before the cutoff |
# | `total_spent` | total value of those orders (use `order_values`) |
# | `days_since_last_order` | as in Exercise 2 (use your function) |
#
# The point of the exercise: **import** the feature functions with `from .features import ...`; do not copy them.
# The grader checks that `report.py` defines no second copy.

# %%
%%writefile {PROJECT}/src/shopfeat/report.py
"""Per-customer summaries built from the feature functions."""
import pandas as pd

### BEGIN SOLUTION
from .features import days_since_last_order, order_values


def customer_summary(orders, items, cutoff):
    cutoff = pd.Timestamp(cutoff)
    past = orders[(orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)].copy()
    past["value"] = past["order_id"].map(order_values(items)).fillna(0.0)
    by_customer = past.groupby("customer_id")
    return pd.DataFrame({
        "n_orders": by_customer.size(),
        "total_spent": by_customer["value"].sum(),
        "days_since_last_order": days_since_last_order(orders, cutoff),
    })
### STARTER
# YOUR CODE HERE: the import, then customer_summary(orders, items, cutoff)
raise NotImplementedError()
### END SOLUTION

# %%
grade("w08.report_module", PROJECT)

# %% [markdown]
# ## 4. `pyproject.toml` and `pip install -e`
#
# **Why.** So far the notebook finds your package because we pointed it at the folder. Other programs (a script, a
# test runner, a colleague's notebook) need it **installed**, like pandas is. Installing needs a description of the
# package: its name, version and dependencies.
#
# **Idea.** That description is `pyproject.toml`, a text file in the TOML format (`key = "value"` lines grouped in
# `[tables]`). Here is the demo's, line by line:
#
# ```toml
# [build-system]                          # how pip turns the folder into an installable package
# requires = ["setuptools>=61"]           # the tool that does the building ...
# build-backend = "setuptools.build_meta" # ... and its entry point. Copy these two lines as they are.
#
# [project]                               # facts about your package
# name = "tinytools"                      # the name pip knows it by (pip install tinytools, pip show tinytools)
# version = "0.1.0"                       # MAJOR.MINOR.PATCH; raise it when you release a change
# description = "Demo package"            # one line, optional
# requires-python = ">=3.9"               # the Python versions it supports
# dependencies = []                       # packages pip must install with it, e.g. ["pandas>=2.0"]
# ```
#
# setuptools finds packages under `src/` on its own, so nothing more is needed. Then:
#
# * `pip install -e <project folder>` installs it in **editable** mode (`-e`): instead of copying your files, pip
#   records a link to your `src/` folder. Edit a file, and every *new* Python process sees the change, with no
#   reinstall. Re-install only when `pyproject.toml` changes.
# * The notebook's own Python was started before the install, so it may not see a newly installed package until you
#   restart it. That is why this notebook keeps using `load_module`, while the `!python ...` commands below start a
#   fresh Python process that sees it straight away.
#
# In a notebook, write `%pip install ...` rather than `!pip install ...`: the `%pip` form always installs into the
# Python that runs this notebook. In a terminal you type `pip install ...` (or `python -m pip install ...`).
#
# **See it.** Install the demo and import it from a *different* folder (`/tmp`), which proves the import does not
# depend on where you stand. Installing takes 10-30 seconds.

# %%
# A TOML file is not Python, so we write it from Python: a triple-quoted string keeps the line breaks.
(DEMO / "pyproject.toml").write_text("""\
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "tinytools"
version = "0.1.0"
description = "Demo package"
requires-python = ">=3.9"
dependencies = []
""")
print((DEMO / "pyproject.toml").read_text())

# %%
%pip install -q -e "{DEMO}"
!cd /tmp && python -c "import tinytools; print('imported', tinytools.__version__, 'from', tinytools.__file__)"

# %% [markdown]
# The output ends with `imported 0.1.0 from .../tinytools/src/tinytools/__init__.py`: the installed package *is*
# your folder. pip may also print a warning about running as root (harmless in Colab) and "you may need to restart
# the kernel": that is the caching explained above, and the reason this notebook uses `load_module`.
#
# **Try it.** Run `!pip show tinytools` and find the version and the location.

# %%
!pip show tinytools

# %% [markdown]
# ### Exercise 7 · `pyproject.toml` for shopfeat
#
# Write `pyproject.toml` in the project folder (`PROJECT`, not inside `src/`): the same `[build-system]`, and a
# `[project]` table with `name = "shopfeat"`, the **same version as `__init__.py`**, `requires-python`, and
# `dependencies` listing pandas (for example `"pandas>=2.0"`).

# %%
(PROJECT / "pyproject.toml").write_text("""\
### BEGIN SOLUTION
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "shopfeat"
version = "0.1.0"
description = "Features and reports for the shop data"
requires-python = ">=3.9"
dependencies = ["pandas>=2.0"]
### STARTER
# YOUR CODE HERE: [build-system] and [project]
### END SOLUTION
""")

# %%
grade("w08.pyproject", PROJECT)

# %% [markdown]
# Now install it. `install_project(PROJECT)` runs exactly `%pip install -q -e "{PROJECT}"`, after checking that you
# finished `pyproject.toml` (so an unfinished exercise never installs a half-written project). Then a fresh Python,
# started in `/tmp`, imports it.

# %%
from mlcourse.graders.w08 import install_project

install_project(PROJECT)

# %%
!cd /tmp && python -c "import shopfeat; print('shopfeat', shopfeat.__version__, 'from', shopfeat.__file__)"

# %% [markdown]
# ### Exercise 8 · what did pip install?
#
# `importlib.metadata.version("name")` asks the installed-package records for a version, the same way `pip show`
# does. Set `installed_version` to the version of `shopfeat` that pip installed. The grader also starts a fresh
# Python in another folder and checks that `import shopfeat` finds *your* project.

# %%
import importlib.metadata

### BEGIN SOLUTION
installed_version = importlib.metadata.version("shopfeat")
### STARTER
installed_version = None  # YOUR CODE HERE
### END SOLUTION
print(installed_version)

# %%
grade("w08.installed_version", installed_version)

# %% [markdown]
# ## 5. A command-line entry point
#
# **Why.** Not everyone who needs your numbers opens a notebook. A scheduled job, a colleague in the terminal or a
# CI pipeline (Week 10) runs a **command**. Packages can install commands.
#
# **Idea.** Two pieces:
#
# 1. a function `main(argv=None)` that reads command-line arguments with **argparse** (Python's standard library for
#    this), does the work, prints the result and returns 0 for success. `argv` is the list of words after the
#    command; `None` means "use the real command line", and passing a list lets tests and graders call it directly;
# 2. a `[project.scripts]` table in `pyproject.toml` that maps a command name to that function:
#    `tinycount = "tinytools.cli:main"` means "the command `tinycount` runs `main` from `tinytools/cli.py`".
#
# argparse in four lines: `parser.add_argument("path")` adds a required **positional** argument;
# `parser.add_argument("--top", type=int, default=5)` an optional **option** with a type and default;
# `required=True` makes an option mandatory; `args = parser.parse_args(argv)` reads them, and wrong input prints a
# usage message and stops the program (it raises `SystemExit`).
#
# **See it.** The demo package gets a `tinycount` command that counts the words in a text file.

# %%
%%writefile {DEMO}/src/tinytools/cli.py
"""Command line for tinytools:  tinycount FILE [--top N]"""
import argparse
import json
from collections import Counter

from .textstats import word_count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count the words in a text file.")
    parser.add_argument("path", help="the text file to read")
    parser.add_argument("--top", type=int, default=3, help="how many frequent words to show")
    args = parser.parse_args(argv)
    with open(args.path) as fh:
        text = fh.read()
    result = {"words": word_count(text), "top": Counter(text.lower().split()).most_common(args.top)}
    print(json.dumps(result))
    return 0

# %%
with open(DEMO / "pyproject.toml", "a") as fh:      # "a" = append to the end of the file
    fh.write('\n[project.scripts]\ntinycount = "tinytools.cli:main"\n')

# %%
(WORK / "demo" / "poem.txt").write_text("the cat and the hat and the bat\n")
%pip install -q -e "{DEMO}"
!tinycount "{WORK}/demo/poem.txt" --top 2
!tinycount --help

# %% [markdown]
# Opening a file with mode `"a"` **appends** to it instead of replacing it. The first command printed
# `{"words": 8, "top": [["the", 3], ["and", 2]]}`; `--help` shows the usage message argparse built for you.
#
# **Try it.** Run `!tinycount` with no file name. Read the error: argparse tells the user exactly what is missing.

# %%
!tinycount

# %% [markdown]
# ### Exercise 9 · `shopfeat/cli.py`
#
# Write `main(argv=None)` in `src/shopfeat/cli.py`. The command takes two positional arguments, the orders CSV and
# the order-items CSV, and a **required** option `--cutoff`. It reads both files (parse `order_date` as dates with
# `pd.read_csv(path, parse_dates=["order_date"])`), builds `customer_summary`, prints **one JSON object** with
#
# - `"cutoff"`: the cutoff text as given,
# - `"active_customers"`: the number of rows in the summary,
# - `"total_spent"`: the sum of `total_spent`, rounded to 2 decimals,
#
# and returns 0. Tip: `json.dumps` cannot write NumPy numbers, so convert with `int(...)` and `float(...)`.

# %%
%%writefile {PROJECT}/src/shopfeat/cli.py
"""Command line for shopfeat:  shopfeat-summary ORDERS_CSV ITEMS_CSV --cutoff YYYY-MM-DD"""
import argparse
import json

import pandas as pd

### BEGIN SOLUTION
from .report import customer_summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarise active customers at a cutoff date.")
    parser.add_argument("orders_csv")
    parser.add_argument("items_csv")
    parser.add_argument("--cutoff", required=True, help="YYYY-MM-DD")
    args = parser.parse_args(argv)
    orders = pd.read_csv(args.orders_csv, parse_dates=["order_date"])
    items = pd.read_csv(args.items_csv)
    summary = customer_summary(orders, items, args.cutoff)
    print(json.dumps({
        "cutoff": args.cutoff,
        "active_customers": int(len(summary)),
        "total_spent": round(float(summary["total_spent"].sum()), 2),
    }))
    return 0
### STARTER
def main(argv=None):
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
grade("w08.cli_main", PROJECT)

# %% [markdown]
# ### Exercise 10 · install the command
#
# Append a `[project.scripts]` table to shopfeat's `pyproject.toml` that creates the command `shopfeat-summary`,
# running `main` from `shopfeat/cli.py`.

# %%
with open(PROJECT / "pyproject.toml", "a") as fh:
    fh.write("""
### BEGIN SOLUTION
[project.scripts]
shopfeat-summary = "shopfeat.cli:main"
### STARTER
# YOUR CODE HERE: the [project.scripts] table
### END SOLUTION
""")

# %%
grade("w08.entry_point", PROJECT)

# %% [markdown]
# The `pyproject.toml` changed, so re-install, then run your command like any other program:

# %%
install_project(PROJECT)

# %%
!shopfeat-summary "{WORK}/data/orders.csv" "{WORK}/data/order_items.csv" --cutoff 2025-06-30

# %%
show_tree(PROJECT)

# %% [markdown]
# You should see `{"cutoff": "2025-06-30", "active_customers": 655, "total_spent": 124301.0}` and a tree with
# `pyproject.toml` and `src/shopfeat/` holding four modules. That is a real, installable Python package.
#
# **Re-running this notebook.** If you run the Exercise 10 cell twice, it appends the table twice and
# the TOML becomes invalid ("Cannot declare ... twice"). Re-run the Exercise 7 cell first: it rewrites the file from
# scratch.

# %% [markdown]
# ## Quiz
#
# **Q1.** Three notebooks each contain their own copy of `order_values`. What is the main benefit of moving it into
# an installed package?
#
# - a) The code runs faster.
# - b) Notebooks cannot be put under version control.
# - c) There is one definition: a fix in one place reaches every notebook, script and test that imports it.
# - d) Packaging automatically tests the function.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.29_q1", answer)

# %% [markdown]
# **Q2.** You fix a bug in `features.py`, save it, and run `import shopfeat.features` again in the same notebook. The
# old behaviour is still there. Why?
#
# - a) The file was not saved.
# - b) Python already imported the module once and returns the cached copy; restart, reload or re-import freshly.
# - c) Notebooks compile modules when the kernel starts.
# - d) The package must be uploaded to PyPI first.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.29_q2", answer)

# %% [markdown]
# **Q3.** What is the main reason for the `src/` layout?
#
# - a) The package can only be imported after it is installed, so you test what users get, not whatever file
#   happens to be in the current folder.
# - b) It makes imports faster.
# - c) pip cannot install packages that are not under `src/`.
# - d) Tests must be inside `src/`.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.29_q3", answer)

# %% [markdown]
# **Q4.** Which statement about `pip install -e .` is right?
#
# - a) It copies your files into site-packages, so later edits are ignored.
# - b) It only works for packages published on PyPI.
# - c) It skips the dependencies listed in `pyproject.toml`.
# - d) It links to your folder, so edits to `.py` files are seen by new Python processes; changes to
#   `pyproject.toml` (dependencies, commands) need a re-install.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.29_q4", answer)

# %% [markdown]
# **Q5.** What does the code under `if __name__ == "__main__":` do?
#
# - a) It never runs.
# - b) It runs when the file is executed as a script (`python file.py`), and not when the file is imported.
# - c) It makes the module compile faster.
# - d) It stops the imports at the top of the file from running.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.29_q5", answer)

# %% [markdown]
# ## Recap
#
# - Pure functions (arguments in, result out, nothing else touched) are the unit of reusable code.
# - A module is a `.py` file; importing runs it once and caches it, so a module should only define things.
# - `if __name__ == "__main__":` separates "run as a script" from "imported as a module".
# - A package is a folder with `__init__.py`; the `src/` layout keeps it importable only once installed.
# - `pyproject.toml` describes the package: `[build-system]`, then `[project]` with name, version,
#   requires-python and dependencies.
# - `pip install -e <folder>` installs it in editable mode; re-install after changing `pyproject.toml`.
# - `[project.scripts]` plus an argparse `main(argv=None)` turns a function into a terminal command.
#
# ## On the job
#
# A new ML engineer's first pull request is often exactly this: moving a function out of a notebook into the team's
# package, with a test. Code review will ask whether it is pure, where it lives, whether something else already does
# the same, and whether the version number needs to change. The command-line entry point is how the same code is
# later run by a scheduler, a Docker container (Week 10) or a CI job, with no notebook in sight.
#
# ## Going further
#
# - Tool guide: [Python packaging and environments](../docs/tools/packaging.md): virtual environments,
#   `requirements.txt` vs `pyproject.toml`, version pins, and common install errors.
# - The advanced track's [package structure notebook](../advanced/notebooks/03_package_structure.ipynb) builds a
#   larger package with the same layout.
# - Next: [30 · Testing with pytest](30_testing_with_pytest.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("29", "reading")
# mark("29", "guided")
