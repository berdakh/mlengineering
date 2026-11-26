# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/32_lab_package_and_test.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 32 · Lab: package and test the churn pipeline
#
# **Week 8 · lab · about 100 minutes**
#
# The retention team liked your churn model from Week 5, and now they want it run every quarter without anyone
# opening a notebook. Your job this week: turn the pipeline into **`churnkit`**, an installable package with a config
# file, logging, a command-line tool and a test suite. When you are done, this is the whole "deployment":
#
# ```bash
# churnkit --config config.yaml --set seed=3
# ```
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c32-01.svg" alt="churnkit: the cli module reads config.yaml through config.py, calls train.py, which uses features.py on the CSV files and writes a log and a run folder; tests check config.py and features.py" style="max-width:100%">
#
# **What you will practise:** everything from notebooks 29-31: modules and a package (29), `pyproject.toml` and a
# command (29), config, logging and run folders (31), and tests that catch real bugs (30). There are no new concepts.
#
# **What you need:** notebooks 29, 30 and 31 open in other tabs. Copying your own code from them is encouraged.
#
# **How grading works:** each exercise writes one or two files; the grader imports them freshly and checks their
# behaviour. Exercise 6 grades your tests by mutation, as in notebook 30.

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
# ## The project folder and the data
#
# The next cell creates the project folder `LAB` with empty `src/churnkit/` and `tests/` folders, and exports three
# tables from the shop database as CSV files into `LAB/data/`: in production, data usually arrives as files like
# these, not as a database the model can query.

# %%
from mlcourse.graders.w08 import work_dir, show_tree, load_module, export_lab_data

LAB = work_dir() / "churnkit"
(LAB / "src" / "churnkit").mkdir(parents=True, exist_ok=True)
(LAB / "tests").mkdir(exist_ok=True)
export_lab_data(LAB / "data")
show_tree(LAB)

# %% [markdown]
# ## Exercise 1 · the package skeleton
#
# Write `LAB/pyproject.toml` and `src/churnkit/__init__.py`:
#
# - `[build-system]` as in notebook 29;
# - `[project]`: `name = "churnkit"`, `version = "0.1.0"`, `requires-python = ">=3.9"`, and `dependencies` listing
#   `pandas`, `scikit-learn` and `pyyaml`;
# - `[project.scripts]`: a command `churnkit` that runs `main` from `churnkit/cli.py`;
# - `[tool.pytest.ini_options]` with `testpaths = ["tests"]`: this table makes `LAB` the root folder for pytest and
#   tells it where the tests are;
# - `__init__.py`: a docstring and `__version__` equal to the version above.

# %%
%%writefile {LAB}/pyproject.toml
### BEGIN SOLUTION
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "churnkit"
version = "0.1.0"
description = "Quarterly churn model for the shop"
requires-python = ">=3.9"
dependencies = ["pandas>=2.0", "scikit-learn>=1.4", "pyyaml>=6"]

[project.scripts]
churnkit = "churnkit.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
### STARTER
# YOUR CODE HERE
### END SOLUTION

# %%
%%writefile {LAB}/src/churnkit/__init__.py
"""churnkit: the shop's churn model as a package."""
### BEGIN SOLUTION
__version__ = "0.1.0"
### STARTER
__version__ = None  # YOUR CODE HERE
### END SOLUTION

# %%
grade("w08.lab_project", LAB)

# %% [markdown]
# ## Exercise 2 · `config.py`
#
# Write `src/churnkit/config.py` with
#
# - a dataclass `Config` with fields `data_dir: str`, `cutoff: str` (both required), `horizon_days: int = 90`,
#   `test_size: float = 0.25`, `seed: int = 0`, `runs_dir: str = "runs"`, `log_file: str = "churnkit.log"`;
# - `load_config(path, overrides=())`: read the YAML file, raise `ValueError` for unknown or missing keys, turn
#   `cutoff` into a string, apply the `key=value` overrides (converted to the field's type; `ValueError` for a bad
#   one) and return a `Config`.
#
# Notebook 31's `load_config` and `apply_overrides` do almost all of this. A useful detail: for a field `f` from
# `dataclasses.fields(Config)`, `f.type` is the class written in the annotation (`int`, `float` or `str`), so
# `f.type("3")` converts text to that type.

# %%
%%writefile {LAB}/src/churnkit/config.py
"""Configuration: a dataclass, and a loader with key checks and command-line overrides."""
from dataclasses import MISSING, dataclass, fields

import yaml

### BEGIN SOLUTION

@dataclass
class Config:
    data_dir: str
    cutoff: str
    horizon_days: int = 90
    test_size: float = 0.25
    seed: int = 0
    runs_dir: str = "runs"
    log_file: str = "churnkit.log"


def load_config(path, overrides=()):
    with open(path) as fh:
        data = yaml.safe_load(fh) or {}
    known = {f.name: f for f in fields(Config)}
    unknown = sorted(set(data) - set(known))
    if unknown:
        raise ValueError(f"unknown config keys: {unknown}")
    if "cutoff" in data:
        data["cutoff"] = str(data["cutoff"])
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep or key not in known:
            raise ValueError(f"bad override {item!r}: use key=value with a known key")
        data[key] = known[key].type(value)
    missing = [name for name, f in known.items() if f.default is MISSING and name not in data]
    if missing:
        raise ValueError(f"missing config keys: {missing}")
    return Config(**data)
### STARTER

@dataclass
class Config:
    data_dir: str
    # YOUR CODE HERE: the other six fields


def load_config(path, overrides=()):
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
grade("w08.lab_config", LAB)

# %% [markdown]
# ## Exercise 3 · `features.py`
#
# Write `src/churnkit/features.py` with
#
# - `FEATURES = ["n_orders", "total_spent", "days_since_last_order", "tenure_days", "segment"]`;
# - `load_data(data_dir)`: read `orders.csv` (parse `order_date`), `order_items.csv` and `customers.csv` (parse
#   `signup_date`) from the folder and return `(orders, items, customers)`;
# - `build_table(orders, items, customers, cutoff, horizon_days=90)`: a DataFrame indexed by `customer_id` (sorted),
#   one row per **active** customer (at least one non-cancelled order on or before the cutoff), with
#
# | column | meaning |
# |---|---|
# | `n_orders` | non-cancelled orders on or before the cutoff |
# | `total_spent` | their total value, quantity × unit_price × (1 − discount) |
# | `days_since_last_order` | days from the last of them to the cutoff |
# | `tenure_days` | days from `signup_date` to the cutoff |
# | `segment` | from `customers` |
# | `churned` | 1 if the customer has **no** non-cancelled order with cutoff < order_date ≤ cutoff + horizon_days, else 0 |
#
# This is notebook 29's `customer_summary` plus Week 4's label. The grader compares your table with a reference on
# a small hand-made dataset and on the shop data at two cutoffs.

# %%
%%writefile {LAB}/src/churnkit/features.py
"""Load the shop CSVs and build the churn table: features from on/before the cutoff, label after it."""
from pathlib import Path

import pandas as pd

FEATURES = ["n_orders", "total_spent", "days_since_last_order", "tenure_days", "segment"]

### BEGIN SOLUTION

def load_data(data_dir):
    folder = Path(data_dir)
    orders = pd.read_csv(folder / "orders.csv", parse_dates=["order_date"])
    items = pd.read_csv(folder / "order_items.csv")
    customers = pd.read_csv(folder / "customers.csv", parse_dates=["signup_date"])
    return orders, items, customers


def order_values(items):
    line = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    return line.groupby(items["order_id"]).sum()


def build_table(orders, items, customers, cutoff, horizon_days=90):
    cutoff = pd.Timestamp(cutoff)
    valid = orders[orders["status"] != "cancelled"].copy()
    valid["value"] = valid["order_id"].map(order_values(items)).fillna(0.0)
    past = valid[valid["order_date"] <= cutoff]
    label_end = cutoff + pd.Timedelta(days=horizon_days)
    came_back = valid[(valid["order_date"] > cutoff) & (valid["order_date"] <= label_end)]["customer_id"]

    by_customer = past.groupby("customer_id")
    table = pd.DataFrame({
        "n_orders": by_customer.size(),
        "total_spent": by_customer["value"].sum(),
        "days_since_last_order": (cutoff - by_customer["order_date"].max()).dt.days,
    })
    info = customers.set_index("customer_id")
    table["tenure_days"] = (cutoff - info["signup_date"]).dt.days
    table["segment"] = info["segment"]
    table["churned"] = (~table.index.isin(came_back)).astype(int)
    table.index.name = "customer_id"
    return table.sort_index()
### STARTER

def load_data(data_dir):
    # YOUR CODE HERE
    raise NotImplementedError()


def build_table(orders, items, customers, cutoff, horizon_days=90):
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
grade("w08.lab_features", LAB)

# %%
features = load_module(LAB, "churnkit.features")
try:
    lab_table = features.build_table(*features.load_data(LAB / "data"), "2025-06-30")
    print(lab_table.shape, "churn rate", round(lab_table["churned"].mean(), 3))
    display(lab_table.head())
except NotImplementedError:
    print("Finish Exercise 3 to see the table.")

# %% [markdown]
# You should see 655 rows, 6 columns and a churn rate of 0.472, the same as `mlcourse.churn.build_churn_table()` in
# notebook 31: two independent implementations agree, which is a test in itself.
#
# ## Exercise 4 · `train.py`
#
# Write `src/churnkit/train.py` with `train(cfg)` that
#
# 1. sets up the logger named `"churnkit"` (`logging.getLogger("churnkit")`) to write to `cfg.log_file`, removing
#    old handlers first (as in notebook 31), level INFO;
# 2. loads the data from `cfg.data_dir` and builds the table at `cfg.cutoff` with `cfg.horizon_days`, then logs an
#    INFO line with the **number of customers** and the churn rate;
# 3. splits `table[FEATURES]` and `table["churned"]`: stratified, `test_size=cfg.test_size`, `random_state=cfg.seed`;
# 4. fits this pipeline on the training rows: a `ColumnTransformer` with `StandardScaler()` on the four numeric
#    features and `OneHotEncoder(handle_unknown="ignore")` on `segment`, followed by
#    `LogisticRegression(max_iter=1000)`;
# 5. computes on the test rows: `accuracy`, `roc_auc` (from `predict_proba(X_test)[:, 1]`), and `baseline_accuracy`:
#    the accuracy of always predicting the most common class of `y_train`; plus `n_train` and `n_test`. All plain
#    `float`/`int`;
# 6. creates a new, uniquely named folder in `cfg.runs_dir` and writes `config.json` (`asdict(cfg)`) and
#    `metrics.json`; logs where it saved them;
# 7. returns the metrics dict with one extra key, `"run_dir"`: the run folder as a string.

# %%
%%writefile {LAB}/src/churnkit/train.py
"""Train and evaluate the churn model described by a Config, and save the run."""
import json
import logging
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .features import FEATURES, build_table, load_data

logger = logging.getLogger("churnkit")
NUMERIC = ["n_orders", "total_spent", "days_since_last_order", "tenure_days"]

### BEGIN SOLUTION

def setup_logging(log_file):
    for old in list(logger.handlers):
        logger.removeHandler(old)
        old.close()
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def make_model():
    prep = ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC),
        ("segment", OneHotEncoder(handle_unknown="ignore"), ["segment"]),
    ])
    return Pipeline([("prep", prep), ("model", LogisticRegression(max_iter=1000))])


def train(cfg):
    setup_logging(cfg.log_file)
    table = build_table(*load_data(cfg.data_dir), cfg.cutoff, cfg.horizon_days)
    logger.info("table at %s: %d customers, churn rate %.3f", cfg.cutoff, len(table), table["churned"].mean())
    X_train, X_test, y_train, y_test = train_test_split(
        table[FEATURES], table["churned"], test_size=cfg.test_size, random_state=cfg.seed,
        stratify=table["churned"])
    model = make_model().fit(X_train, y_train)
    majority = int(y_train.mode()[0])
    metrics = {
        "accuracy": float(accuracy_score(y_test, model.predict(X_test))),
        "roc_auc": float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])),
        "baseline_accuracy": float((y_test == majority).mean()),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    logger.info("metrics: %s", metrics)
    run_dir = Path(cfg.runs_dir) / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(json.dumps(asdict(cfg), indent=2))
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    logger.info("saved run to %s", run_dir)
    return {**metrics, "run_dir": str(run_dir)}
### STARTER

def train(cfg):
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
grade("w08.lab_train", LAB)

# %% [markdown]
# ## Exercise 5 · `cli.py`
#
# Write `main(argv=None)` in `src/churnkit/cli.py`: an argparse parser with a **required** `--config` option and a
# repeatable `--set` option (`action="append", default=[]` collects every `--set key=value` into a list). Load the
# config with the overrides, run `train`, print the returned metrics with `json.dumps(metrics, indent=2)`, and
# return 0.

# %%
%%writefile {LAB}/src/churnkit/cli.py
"""Command line:  churnkit --config config.yaml [--set key=value ...]"""
import argparse
import json

from .config import load_config
from .train import train

### BEGIN SOLUTION

def main(argv=None):
    parser = argparse.ArgumentParser(description="Train and evaluate the churn model.")
    parser.add_argument("--config", required=True, help="path to the YAML config file")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="override one config value (repeatable)")
    args = parser.parse_args(argv)
    cfg = load_config(args.config, args.set)
    metrics = train(cfg)
    print(json.dumps(metrics, indent=2))
    return 0
### STARTER

def main(argv=None):
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
grade("w08.lab_cli", LAB)

# %% [markdown]
# ## Exercise 6 · tests that protect the pipeline
#
# Write `tests/test_features.py` and `tests/test_config.py`. The grader runs your suite against a correct `churnkit`
# (it must pass) and against six copies, each with one bug that a real teammate could plausibly introduce (each must
# make at least one test fail). Your tests should check these rules, using **small hand-made tables** (not the CSV
# files):
#
# - cancelled orders count for nothing (neither in `n_orders` nor in `total_spent`);
# - discounts reduce `total_spent`;
# - orders **after** the cutoff never change the features (and do not make a customer "active");
# - the label window is `cutoff < order_date <= cutoff + horizon_days`: an order **exactly** `horizon_days` after the
#   cutoff means the customer did *not* churn;
# - `load_config` rejects an unknown key (`pytest.raises(ValueError)`; write the YAML into `tmp_path`);
# - overrides are converted to the right type (`--set seed=3` gives the int 3).
#
# Rules for this exercise: tests import only `churnkit.features` and `churnkit.config`; keep helpers inside the
# `test_*.py` files. Tip from notebook 30: give orders very different values (1, 10, 100, 1000) so a wrong total tells
# you which order was miscounted.

# %%
%%writefile {LAB}/tests/test_features.py
import pandas as pd
import pytest

from churnkit.features import build_table

### BEGIN SOLUTION
CUTOFF = "2025-03-31"          # with horizon 90 days, the label window ends on 2025-06-29


@pytest.fixture
def shop():
    orders = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 6, 7],
        "customer_id": [1, 1, 1, 2, 2, 3, 4],
        "order_date": pd.to_datetime(["2025-03-01", "2025-03-20", "2025-06-29", "2025-03-31", "2025-04-15",
                                      "2025-07-15", "2025-01-10"]),
        "status": ["delivered", "cancelled", "delivered", "delivered", "delivered", "delivered", "delivered"],
    })
    items = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 6, 7],
        "quantity": [2, 1, 1, 1, 1, 1, 1],
        "unit_price": [10.0, 1000.0, 1.0, 7.0, 500.0, 3.0, 4.0],
        "discount": [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    })
    customers = pd.DataFrame({
        "customer_id": [1, 2, 3, 4],
        "signup_date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-07-01", "2024-12-31"]),
        "segment": ["consumer", "business", "consumer", "consumer"],
    })
    return orders, items, customers


def test_one_row_per_active_customer(shop):
    table = build_table(*shop, CUTOFF, 90)
    assert sorted(table.index) == [1, 2, 4]          # customer 3 only ordered after the cutoff


def test_cancelled_orders_and_discounts(shop):
    table = build_table(*shop, CUTOFF, 90)
    assert table.loc[1, "n_orders"] == 1
    assert table.loc[1, "total_spent"] == pytest.approx(10.0)   # 2 * 10 * (1 - 0.5); the cancelled 1000 ignored


def test_orders_after_the_cutoff_do_not_change_features(shop):
    table = build_table(*shop, CUTOFF, 90)
    assert table.loc[2, "n_orders"] == 1
    assert table.loc[2, "total_spent"] == pytest.approx(7.0)
    assert table.loc[2, "days_since_last_order"] == 0


def test_label_window(shop):
    table = build_table(*shop, CUTOFF, 90)
    assert table.loc[1, "churned"] == 0    # ordered exactly on cutoff + 90 days
    assert table.loc[2, "churned"] == 0    # ordered inside the window
    assert table.loc[4, "churned"] == 1    # no order after the cutoff
### STARTER

def test_build_table():
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
%%writefile {LAB}/tests/test_config.py
import pytest

from churnkit.config import load_config

### BEGIN SOLUTION

def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_unknown_key_is_rejected(tmp_path):
    path = write(tmp_path, "data_dir: data\ncutoff: 2025-06-30\nhorizon: 30\n")
    with pytest.raises(ValueError):
        load_config(path)


def test_overrides_are_converted(tmp_path):
    path = write(tmp_path, "data_dir: data\ncutoff: 2025-06-30\n")
    cfg = load_config(path, ["seed=3", "test_size=0.4"])
    assert cfg.seed == 3 and isinstance(cfg.seed, int)
    assert cfg.test_size == pytest.approx(0.4)
    assert cfg.cutoff == "2025-06-30"
### STARTER

def test_load_config(tmp_path):
    # YOUR CODE HERE
    raise NotImplementedError()
### END SOLUTION

# %%
!cd "{LAB}" && PYTHONPATH=src python -m pytest -q

# %%
grade("w08.lab_tests", LAB)

# %% [markdown]
# (`PYTHONPATH=src` lets this run find the package before you install it in the next step; after `pip install -e`,
# plain `python -m pytest` works too.)
#
# ## Exercise 7 · run it like production
#
# Everything is in place. The next cells write the config file, install the package, run the command twice (the
# second time with an override), run the test suite, and show the log. Read every output. Then set `lab_run_dir` to
# the folder of the run with `seed` 0. Hint: `(LAB / "runs").iterdir()` lists the run folders, and each one has a
# `config.json` you can read with `json.loads(path.read_text())`. (Sorting by name is not enough: two runs started
# in the same second have names that differ only in their random part.)

# %%
%%writefile {LAB}/config.yaml
# Settings for one quarterly churn run. Paths are relative to the project folder.
data_dir: data
cutoff: "2025-06-30"
horizon_days: 90
test_size: 0.25
seed: 0
runs_dir: runs
log_file: churnkit.log

# %%
import shutil

shutil.rmtree(LAB / "runs", ignore_errors=True)       # start from an empty runs/ folder
if "YOUR CODE HERE" in (LAB / "pyproject.toml").read_text():
    print("Finish Exercise 1 first.")
else:
    %pip install -q -e "{LAB}"
    !cd "{LAB}" && churnkit --config config.yaml
    !cd "{LAB}" && churnkit --config config.yaml --set seed=3
    !cd "{LAB}" && python -m pytest -q
    !tail -n 6 "{LAB}/churnkit.log"

# %%
### BEGIN SOLUTION
import json

lab_run_dir = next(d for d in (LAB / "runs").iterdir()
                   if json.loads((d / "config.json").read_text())["seed"] == 0)
### STARTER
lab_run_dir = None  # YOUR CODE HERE
### END SOLUTION
print(lab_run_dir)

# %%
grade("w08.lab_run", lab_run_dir)

# %%
show_tree(LAB)

# %% [markdown]
# ## Quiz
#
# **Q1.** In `churnkit`, which split of responsibilities is right?
#
# - a) Everything should stay in one notebook so it is easy to read.
# - b) The config file should contain the feature logic, so it can change without code changes.
# - c) The package holds the logic once, the config holds what changes between runs, the CLI connects them, the tests
#   protect the logic, and each run folder records what happened.
# - d) Tests replace evaluation, so `metrics.json` is not needed.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.32_q1", answer)

# %% [markdown]
# **Q2.** What did the grader of Exercise 6 measure?
#
# - a) Whether your tests notice realistic bugs: they must pass on correct code and fail on each planted bug.
# - b) The accuracy of your model.
# - c) The percentage of lines your tests execute.
# - d) How fast your tests run.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.32_q2", answer)

# %% [markdown]
# **Q3.** A reviewer asks you to reproduce the ROC AUC in last quarter's report. What makes that possible?
#
# - a) Nothing: results with randomness cannot be reproduced.
# - b) The metrics file alone.
# - c) The log file alone.
# - d) The run folder's `config.json` (with the seed), the code version, and the same data and library versions:
#   rerun the command with that config and compare.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.32_q3", answer)

# %% [markdown]
# **Q4.** A teammate changes `<= label_end` to `< label_end` in `build_table`. Which safeguard catches it?
#
# - a) The ROC AUC: it will drop clearly.
# - b) A unit test with an order exactly `horizon_days` after the cutoff.
# - c) Python's type checks.
# - d) The INFO lines in the log.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w08.32_q4", answer)

# %% [markdown]
# ## Reflection
#
# Write a few sentences for yourself (not graded):
#
# 1. Which planted bug in Exercise 6 did your first version of the tests miss, and why was it easy to miss?
# 2. Run `churnkit --config config.yaml --set seed=1` and `--set seed=2`. How much does the ROC AUC move between
#    seeds? What does that tell you about reporting one number to three decimals?
# 3. What would you still need before a scheduler could run `churnkit` every quarter unattended? (Weeks 9-11 answer
#    much of this.)
#
# ## What to show in your portfolio
#
# The `churnkit` folder is a small but complete ML package: a `pyproject.toml` with a command, a config file,
# logging, run folders and a test suite that catches realistic bugs. Download it (or copy it to Google Drive), put it
# in a Git repository (notebook 03), and write a short README: what it does, how to install it
# (`pip install -e .`), how to run it (`churnkit --config config.yaml`), how to test it (`python -m pytest`), and the
# metrics of one run next to the baseline. Never commit the data files of a real employer; here the data is
# synthetic, so it is fine.

# %% [markdown]
# ## Going further
#
# - Tool guides: [Python packaging and environments](../docs/tools/packaging.md) and [pytest](../docs/tools/pytest.md).
# - Next week: saving the trained model and serving predictions through an API, starting with
#   [33 · Saving models and batch prediction](33_saving_models_batch.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("32", "reading")
# mark("32", "guided")
